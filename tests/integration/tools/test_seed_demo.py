"""`sgs-admin seed demo` (010/T2): 30 tuplas, casos especiais, idempotência, recusa em prod."""

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from src.core.config import AppEnv
from src.tools.seed_demo import SeedRecusado, carregar
from tests.factories import make_settings
from tests.integration.postgres import BancoDeTeste, motor

TABELAS_DE_NEGOCIO = ("health_units", "equipments", "services", "users", "role_assignments")


async def _contagens(url: str) -> dict[str, int]:
    engine = motor(url)
    async with engine.connect() as conexao:
        contagens = {
            tabela: int(await conexao.scalar(text(f"SELECT count(*) FROM {tabela}")))  # noqa: S608
            for tabela in (*TABELAS_DE_NEGOCIO, "audit_log")
        }
    await engine.dispose()
    return contagens


async def test_seed_carrega_30_ou_mais_por_tabela_e_e_idempotente(banco: BancoDeTeste) -> None:
    """010/R1.1, R1.2, R1.4 (disciplina de BD: 30 tuplas nas tabelas de negócio)."""
    settings = make_settings(database_url=SecretStr(banco.url_api))

    primeira = await carregar(banco.url_api, settings, senha="senha-demo-123")
    depois_da_primeira = await _contagens(banco.url_api)
    segunda = await carregar(banco.url_api, settings, senha="senha-demo-123")
    depois_da_segunda = await _contagens(banco.url_api)

    for tabela in TABELAS_DE_NEGOCIO:
        assert depois_da_primeira[tabela] >= 30, tabela
    assert {k: v for k, v in depois_da_segunda.items() if k != "audit_log"} == {
        k: v for k, v in depois_da_primeira.items() if k != "audit_log"
    }
    assert depois_da_segunda["audit_log"] == depois_da_primeira["audit_log"]  # nada novo
    assert primeira.criados["unidades"] == 37
    assert segunda.criados == {}


async def test_seed_tem_os_casos_especiais_do_cliente(banco: BancoDeTeste) -> None:
    """010/R1.2, R1.3."""
    await carregar(
        banco.url_api, make_settings(database_url=SecretStr(banco.url_api)), senha="x" * 12
    )
    engine = motor(banco.url_api)
    async with engine.connect() as conexao:
        consultas = {
            "equipamento sem unidade": "SELECT count(*) FROM equipments WHERE unit_id IS NULL",
            "serviço solto": "SELECT count(*) FROM services WHERE unit_id IS NULL",
            "unidade sem CNES": "SELECT count(*) FROM health_units WHERE cnes IS NULL",
            "serviço fora do CNES": "SELECT count(*) FROM services WHERE NOT in_cnes",
            "unidade com pendência": "SELECT count(*) FROM health_units WHERE pending_issues > 0",
            "unidade com dois equipamentos": (
                "SELECT count(*) FROM (SELECT unit_id FROM equipments WHERE unit_id IS NOT NULL"
                " GROUP BY unit_id HAVING count(*) >= 2) AS d"
            ),
            "unidade ativa sem serviço": (
                "SELECT count(*) FROM health_units AS u WHERE status = 'ativa'"
                " AND NOT EXISTS (SELECT 1 FROM services AS s WHERE s.unit_id = u.id)"
            ),
            "CAPS com farmácia": (
                "SELECT count(*) FROM services AS s JOIN health_units AS u ON u.id = s.unit_id"
                " JOIN unit_types AS t ON t.id = u.unit_type_id"
                " WHERE t.code LIKE 'CAPS%' AND s.name LIKE 'Farmácia%'"
            ),
            "distritos cobertos": "SELECT count(DISTINCT district_id) FROM health_units",
            "papéis cobertos": "SELECT count(DISTINCT role_id) FROM role_assignments",
        }
        resultado = {nome: int(await conexao.scalar(text(sql))) for nome, sql in consultas.items()}
    await engine.dispose()

    assert all(valor > 0 for valor in resultado.values()), resultado
    assert resultado["distritos cobertos"] == 8
    assert resultado["papéis cobertos"] == 7


async def test_seed_recusado_em_prod(banco: BancoDeTeste) -> None:
    """010/R1.6."""
    settings = make_settings(database_url=SecretStr(banco.url_api), app_env=AppEnv.TEST)
    prod = settings.model_copy(update={"app_env": AppEnv.PROD})

    with pytest.raises(SeedRecusado):
        await carregar(banco.url_api, prod, senha="x" * 12)
