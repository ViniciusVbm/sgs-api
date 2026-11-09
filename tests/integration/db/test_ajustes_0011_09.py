"""Ajustes de base da 0011_09 (emenda 011/T21 e T22, de 09/11/2026).

Índices das FKs de equipamento e serviço, CHECKs de status e quantidade, `updated_at` por
trigger, DELETE revogado das tabelas de exclusão lógica, EXECUTE revogado de PUBLIC e o escopo de
`dashboard:read` por papel.
"""

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.integration.postgres import BancoDeTeste, motor
from tests.integration.registry.cadastro import inserir_equipamento, inserir_unidade


@pytest.mark.parametrize(
    ("indice", "tabela", "coluna"),
    [
        ("ix_equipments_unit_id", "equipments", "unit_id"),
        ("ix_services_equipment_id", "services", "equipment_id"),
    ],
)
async def test_indices_das_fks_existem(
    banco: BancoDeTeste, indice: str, tabela: str, coluna: str
) -> None:
    """011/T21: as FKs RESTRICT e SET NULL têm índice na coluna de origem."""
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        definicao = await conexao.scalar(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = :indice"), {"indice": indice}
        )
    await engine.dispose()

    assert definicao is not None
    assert f"ON public.{tabela} USING btree ({coluna})" in definicao


@pytest.mark.parametrize(
    ("sql", "restricao"),
    [
        (
            "UPDATE equipments SET status = 'quebrado' WHERE id = :id",
            "ck_equipments_status_valido",
        ),
        ("UPDATE equipments SET quantity = 0 WHERE id = :id", "ck_equipments_quantity_positiva"),
    ],
)
async def test_checks_do_equipamento_recusam_valor_invalido(
    banco: BancoDeTeste, sql: str, restricao: str
) -> None:
    """011/T21: status fora do domínio e quantidade não positiva são recusados pelo banco."""
    engine = motor(banco.url_api)
    async with engine.begin() as conexao:
        unidade = await inserir_unidade(conexao, "CAPS Teste")
        equipamento = await inserir_equipamento(conexao, unidade)
    with pytest.raises(IntegrityError, match=restricao):
        async with engine.begin() as conexao:
            await conexao.execute(text(sql), {"id": equipamento})
    await engine.dispose()


async def test_check_do_servico_recusa_status_invalido(banco: BancoDeTeste) -> None:
    """011/T21: serviço só `ativo` ou `inativo`."""
    engine = motor(banco.url_api)
    with pytest.raises(IntegrityError, match="ck_services_status_valido"):
        async with engine.begin() as conexao:
            await conexao.execute(
                text(
                    "INSERT INTO services (id, service_type_id, name, status)"
                    " VALUES (gen_random_uuid(), (SELECT min(id) FROM service_types),"
                    " 'Sala', 'suspenso')"
                )
            )
    await engine.dispose()


async def test_updated_at_avanca_quando_o_equipamento_muda(banco: BancoDeTeste) -> None:
    """011/T21: `updated_at` acompanha a alteração, mesmo com SQL escrito à mão."""
    engine = motor(banco.url_api)
    async with engine.begin() as conexao:
        unidade = await inserir_unidade(conexao, "CAPS Relógio")
        equipamento = await inserir_equipamento(conexao, unidade)
        antes = await conexao.scalar(
            text("SELECT updated_at FROM equipments WHERE id = :id"), {"id": equipamento}
        )
    await asyncio.sleep(0.01)
    async with engine.begin() as conexao:
        await conexao.execute(
            text("UPDATE equipments SET quantity = 3 WHERE id = :id"), {"id": equipamento}
        )
        depois = await conexao.scalar(
            text("SELECT updated_at FROM equipments WHERE id = :id"), {"id": equipamento}
        )
    async with engine.begin() as conexao:
        await conexao.execute(
            text("UPDATE equipments SET quantity = 3 WHERE id = :id"), {"id": equipamento}
        )
        sem_mudanca = await conexao.scalar(
            text("SELECT updated_at FROM equipments WHERE id = :id"), {"id": equipamento}
        )
    await engine.dispose()

    assert depois > antes
    assert sem_mudanca == depois


@pytest.mark.parametrize(
    "tabela",
    [
        "health_units",
        "districts",
        "technical_areas",
        "unit_types",
        "equipment_types",
        "service_types",
    ],
)
async def test_api_nao_apaga_tabelas_de_exclusao_logica(banco: BancoDeTeste, tabela: str) -> None:
    """006/R4.2, 011/T21: o login da API não tem DELETE onde a exclusão é só lógica."""
    engine = motor(banco.url_api)
    with pytest.raises(DBAPIError, match="permission denied"):
        async with engine.begin() as conexao:
            await conexao.execute(text(f"DELETE FROM {tabela} WHERE false"))  # noqa: S608
    await engine.dispose()


@pytest.mark.parametrize("tabela", ["equipments", "services"])
async def test_api_ainda_apaga_equipamentos_e_servicos(banco: BancoDeTeste, tabela: str) -> None:
    """Decisão U5 da 011: equipamentos e serviços têm exclusão física."""
    engine = motor(banco.url_api)
    async with engine.begin() as conexao:
        await conexao.execute(text(f"DELETE FROM {tabela} WHERE false"))  # noqa: S608
    await engine.dispose()


@pytest.mark.parametrize("funcao", ["audit_log_somente_insercao()", "trg_roles_protect_system()"])
async def test_funcoes_de_trigger_antigas_sem_execute_para_public(
    banco: BancoDeTeste, funcao: str
) -> None:
    """011/T21, 011/R10.1: só os triggers chamam essas funções."""
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        acl = await conexao.scalar(
            text("SELECT proacl::text FROM pg_proc WHERE oid = CAST(:f AS regprocedure)"),
            {"f": funcao},
        )
    await engine.dispose()

    assert acl is not None
    # Na ACL, a entrada de PUBLIC é a que não tem papel antes do `=` (ex.: `=X/dono`).
    entradas = acl.strip("{}").split(",")
    assert not [entrada for entrada in entradas if entrada.startswith("=")]


async def test_dashboard_read_tem_o_escopo_de_cada_papel(banco: BancoDeTeste) -> None:
    """011/T22 (D3): menor privilégio no dashboard."""
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        linhas = await conexao.execute(
            text(
                "SELECT r.code, rp.max_scope FROM role_permissions AS rp"
                " JOIN roles AS r ON r.id = rp.role_id"
                " JOIN permissions AS p ON p.id = rp.permission_id"
                " WHERE p.code = 'dashboard:read'"
            )
        )
        escopos = dict(linhas.all())
    await engine.dispose()

    assert escopos == {
        "GESTOR_DADOS": "global",
        "COORD_TECNICO": "area",
        "TECNICO_DISTRITAL": "distrito",
        "GESTOR_UNIDADE": "unidade",
        "DIRETORIA": "global",
    }
