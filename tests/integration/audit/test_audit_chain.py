"""audit.registrar: mesma transação do caso de uso e hash encadeado (spec 001, R5.1 e R5.3)."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from functools import partial
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.audit.application.registrar import Ator, Entidade, Mudanca, registrar
from src.modules.audit.domain.entry import GENESIS_HASH, AuditEntry
from src.modules.audit.infrastructure.repository import SqlAuditStore
from tests.integration.postgres import BancoDeTeste, motor

USUARIO = UUID("01928a3b-0000-7000-8000-000000000001")
SESSAO = UUID("01928a3b-0000-7000-8000-0000000000aa")


class FalhaSimuladaError(Exception):
    pass


@pytest.fixture
async def sessoes(banco: BancoDeTeste) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Sessões com o login da API: só INSERT e SELECT na trilha, como em produção."""
    engine = motor(banco.url_api)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _registrar(sessoes: async_sessionmaker[AsyncSession], acao: str) -> AuditEntry:
    async with sessoes() as sessao, sessao.begin():
        return await registrar(
            SqlAuditStore(sessao),
            acao=acao,
            ator=Ator(tipo="usuario", user_id=USUARIO, ip="10.0.0.1", request_id=f"req-{acao}"),
        )


async def _trilha(sessoes: async_sessionmaker[AsyncSession]) -> list[dict[str, Any]]:
    async with sessoes() as sessao:
        resultado = await sessao.execute(text("SELECT * FROM audit_log ORDER BY id"))
        return [dict(linha) for linha in resultado.mappings()]


async def _cabeca(sessoes: async_sessionmaker[AsyncSession]) -> str:
    async with sessoes() as sessao:
        return str(await sessao.scalar(text("SELECT last_hash FROM audit_chain_head")))


def _do_banco(linha: dict[str, Any]) -> AuditEntry:
    """Reconstrói o registro a partir da linha gravada, como faria uma verificação da trilha."""
    return AuditEntry(
        occurred_at=linha["occurred_at"],
        action=linha["action"],
        actor=Ator(
            user_id=linha["actor_user_id"],
            papeis=tuple(linha["actor_roles"]),
            session_id=linha["session_id"],
            ip=linha["ip"],
            request_id=linha["request_id"],
            tipo=linha.get("actor_type"),
            origem=linha.get("origin"),
            user_agent=linha.get("user_agent"),
        ),
        entity=(
            Entidade(tipo=linha["entity_type"], id=linha["entity_id"])
            if linha["entity_type"]
            else None
        ),
        changes=tuple(Mudanca(**mudanca) for mudanca in linha["changes"]),
        metadata=linha["metadata"],
        prev_hash=linha["prev_hash"],
        hash=linha["hash"],
        result=linha.get("result"),
        result_reason=linha.get("result_reason"),
    )


def _assert_cadeia_integra(trilha: list[dict[str, Any]], cabeca: str) -> None:
    anterior = GENESIS_HASH
    for linha in trilha:
        registro = _do_banco(linha)
        assert registro.prev_hash == anterior
        assert registro.recompute_hash() == registro.hash
        anterior = registro.hash
    assert cabeca == anterior


async def test_registra_na_transacao_do_caso_de_uso_com_todos_os_campos(
    sessoes: async_sessionmaker[AsyncSession],
) -> None:
    """001/R5.1"""
    async with sessoes() as sessao, sessao.begin():
        registro = await registrar(
            SqlAuditStore(sessao),
            acao="unidade.atualizada",
            entidade=Entidade(tipo="unidade", id="42"),
            mudancas=[Mudanca(campo="telefone", de="8133330000", para="8133331111")],
            ator=Ator(
                tipo="usuario",
                user_id=USUARIO,
                papeis=("GESTOR_DADOS",),
                session_id=SESSAO,
                ip="10.0.0.1",
                request_id="req-1",
            ),
            metadados={"user_agent": "teste"},
        )

    [linha] = await _trilha(sessoes)
    assert linha["action"] == "unidade.atualizada"
    assert (linha["entity_type"], linha["entity_id"]) == ("unidade", "42")
    assert linha["changes"] == [{"campo": "telefone", "de": "8133330000", "para": "8133331111"}]
    assert linha["actor_user_id"] == USUARIO
    assert linha["actor_roles"] == ["GESTOR_DADOS"]
    assert (linha["session_id"], linha["ip"], linha["request_id"]) == (SESSAO, "10.0.0.1", "req-1")
    assert linha["metadata"] == {"user_agent": "teste"}
    assert linha["hash"] == registro.hash
    assert linha["occurred_at"] == registro.occurred_at


async def test_falha_no_caso_de_uso_desfaz_a_auditoria(
    sessoes: async_sessionmaker[AsyncSession],
) -> None:
    """001/R5.1"""

    async def caso_de_uso_que_falha_depois_de_auditar() -> None:
        async with sessoes() as sessao, sessao.begin():
            await registrar(
                SqlAuditStore(sessao), acao="unidade.atualizada", ator=Ator(tipo="sistema")
            )
            raise FalhaSimuladaError

    with pytest.raises(FalhaSimuladaError):
        await caso_de_uso_que_falha_depois_de_auditar()

    assert await _trilha(sessoes) == []
    assert await _cabeca(sessoes) == GENESIS_HASH


async def test_cada_registro_encadeia_no_anterior(
    sessoes: async_sessionmaker[AsyncSession],
) -> None:
    """001/R5.3"""
    for acao in ("unidade.criada", "unidade.atualizada", "auth.login"):
        await _registrar(sessoes, acao)

    trilha = await _trilha(sessoes)
    assert [linha["action"] for linha in trilha] == [
        "unidade.criada",
        "unidade.atualizada",
        "auth.login",
    ]
    _assert_cadeia_integra(trilha, await _cabeca(sessoes))


async def test_transacoes_simultaneas_nao_bifurcam_a_cadeia(
    sessoes: async_sessionmaker[AsyncSession],
) -> None:
    """001/R5.3"""
    await asyncio.gather(*(_registrar(sessoes, f"teste.evento_{n}") for n in range(8)))

    trilha = await _trilha(sessoes)
    assert len(trilha) == 8
    _assert_cadeia_integra(trilha, await _cabeca(sessoes))


# --- Spec 013, T1: colunas de origem e resultado (migração 0013_01)


def _migrar_ate(conexao: Any, revisao: str) -> None:
    from alembic import command

    from src.core.db import alembic_config

    config = alembic_config()
    config.attributes["connection"] = conexao
    command.upgrade(config, revisao)


async def _migrar(url_dono: str, revisao: str) -> None:
    engine = motor(url_dono)
    async with engine.connect() as conexao:
        await conexao.run_sync(_migrar_ate, revisao)
        await conexao.commit()
    await engine.dispose()


async def _registrar_como_antes_da_013(
    sessoes: async_sessionmaker[AsyncSession], acao: str
) -> AuditEntry:
    """Grava como o `SqlAuditStore` de antes da 013: só as colunas que existiam na 0011_09."""
    async with sessoes() as sessao, sessao.begin():
        anterior = await sessao.scalar(
            text("SELECT last_hash FROM audit_chain_head WHERE id = 1 FOR UPDATE")
        )
        entrada = AuditEntry.create(
            prev_hash=str(anterior),
            occurred_at=datetime.now(UTC),
            action=acao,
            actor=Ator(user_id=USUARIO, ip="10.0.0.1", request_id=f"req-{acao}"),
        )
        conteudo = entrada.content()
        await sessao.execute(
            text(
                "INSERT INTO audit_log (occurred_at, actor_user_id, actor_roles, session_id, ip,"
                " request_id, action, entity_type, entity_id, changes, metadata, prev_hash, hash)"
                " VALUES (:quando, :usuario, CAST(:papeis AS jsonb), NULL, :ip, :req, :acao,"
                " NULL, NULL, '[]', '{}', :prev, :hash)"
            ),
            {
                "quando": entrada.occurred_at,
                "usuario": USUARIO,
                "papeis": "[]",
                "ip": conteudo["ip"],
                "req": conteudo["request_id"],
                "acao": acao,
                "prev": entrada.prev_hash,
                "hash": entrada.hash,
            },
        )
        await sessao.execute(
            text("UPDATE audit_chain_head SET last_hash = :hash WHERE id = 1"),
            {"hash": entrada.hash},
        )
    return entrada


async def test_cadeia_antiga_continua_integra_apos_migracao(banco_vazio: BancoDeTeste) -> None:
    """013/R1.5: eventos gravados antes da 0013_01 continuam com o mesmo hash e com os campos novos
    nulos; os eventos novos encadeiam neles com os campos preenchidos."""
    await _migrar(banco_vazio.url_dono, "0011_09")
    engine = motor(banco_vazio.url_api)
    sessoes = async_sessionmaker(engine, expire_on_commit=False)
    antigos = [
        await _registrar_como_antes_da_013(sessoes, acao)
        for acao in ("unidade.criada", "unidade.atualizada")
    ]

    await _migrar(banco_vazio.url_dono, "head")
    async with sessoes() as sessao, sessao.begin():
        novo = await registrar(
            SqlAuditStore(sessao),
            acao="unidade.desativada",
            ator=Ator(
                user_id=USUARIO, tipo="usuario", origem="api", user_agent="Mozilla/5.0 (teste)"
            ),
            resultado="success",
        )
    trilha = await _trilha(sessoes)
    cabeca = await _cabeca(sessoes)
    await engine.dispose()

    assert [linha["hash"] for linha in trilha] == [*(e.hash for e in antigos), novo.hash]
    for linha in trilha[:2]:
        colunas = ("actor_type", "origin", "user_agent", "result", "result_reason")
        assert all(linha[coluna] is None for coluna in colunas)
    assert (trilha[2]["actor_type"], trilha[2]["origin"], trilha[2]["result"]) == (
        "usuario",
        "api",
        "success",
    )
    assert trilha[2]["user_agent"] == "Mozilla/5.0 (teste)"
    _assert_cadeia_integra(trilha, cabeca)


def _fixo(instante: datetime) -> datetime:
    return instante


async def test_instante_preserva_microssegundos_e_ordem_por_id(
    sessoes: async_sessionmaker[AsyncSession],
) -> None:
    """013/R2.3: `timestamptz` em UTC com microssegundos; a ordem da cadeia é a do `id`, mesmo que
    os instantes não estejam em ordem."""
    instantes = [
        datetime(2026, 11, 11, 15, 0, 0, 654321, tzinfo=UTC),
        datetime(2026, 11, 11, 14, 59, 59, 1, tzinfo=UTC),
    ]
    for instante in instantes:
        async with sessoes() as sessao, sessao.begin():
            await registrar(
                SqlAuditStore(sessao),
                acao="unidade.atualizada",
                ator=Ator(tipo="sistema", origem="teste"),
                resultado="success",
                agora=partial(_fixo, instante),
            )

    trilha = await _trilha(sessoes)

    assert [linha["occurred_at"] for linha in trilha] == instantes
    assert trilha[0]["id"] < trilha[1]["id"]
    _assert_cadeia_integra(trilha, await _cabeca(sessoes))


VALORES_INVALIDOS = {
    "tipo": {"actor_type": "robo"},
    "resultado": {"result": "talvez"},
    "falha_sem_categoria": {"result": "failure"},
    "sucesso_com_categoria": {"result": "success", "result_reason": "conflito"},
    "usuario_sem_id": {"actor_type": "usuario"},
}


@pytest.mark.parametrize("valores", VALORES_INVALIDOS.values(), ids=VALORES_INVALIDOS.keys())
async def test_valor_fora_do_dominio_e_recusado(
    sessoes: async_sessionmaker[AsyncSession], valores: dict[str, str]
) -> None:
    """013/R1.1, R1.2, R4.1: os CHECKs da 0013_01 recusam o que o domínio também recusa, mesmo
    num INSERT que não passa pelo `registrar`."""
    # Nomes de coluna fixos (VALORES_INVALIDOS); os valores vão como parâmetros.
    colunas = ", ".join(valores)
    parametros = ", ".join(f":{c}" for c in valores)
    insercao = f"INSERT INTO audit_log (occurred_at, action, prev_hash, hash, {colunas}) VALUES (now(), 'unidade.atualizada', :prev, :hash, {parametros})"  # noqa: E501, S608
    with pytest.raises(IntegrityError, match="ck_audit_log_"):
        async with sessoes() as sessao, sessao.begin():
            await sessao.execute(text(insercao), {"prev": "1" * 64, "hash": "2" * 64, **valores})


# --- Spec 013, T7: tipo de ator e resultado obrigatórios (migração 0013_02, NOT VALID)


async def test_insert_sem_tipo_ou_resultado_e_recusado(
    sessoes: async_sessionmaker[AsyncSession],
) -> None:
    """013/R1.6: evento novo sem tipo de ator ou sem resultado é recusado pelo banco, e pelo
    próprio `registrar` quando o ator não diz o tipo; a constraint segue NOT VALID."""
    for colunas in ({"result": "success"}, {"actor_type": "sistema"}):
        nomes = ", ".join(colunas)
        valores = ", ".join(f":{c}" for c in colunas)
        insercao = f"INSERT INTO audit_log (occurred_at, action, prev_hash, hash, {nomes}) VALUES (now(), 'unidade.atualizada', :prev, :hash, {valores})"  # noqa: E501, S608
        with pytest.raises(IntegrityError, match="ck_audit_log_origem_obrigatoria"):
            async with sessoes() as sessao, sessao.begin():
                await sessao.execute(
                    text(insercao), {"prev": "1" * 64, "hash": "2" * 64, **colunas}
                )
    with pytest.raises(IntegrityError, match="ck_audit_log_origem_obrigatoria"):
        async with sessoes() as sessao, sessao.begin():
            await registrar(SqlAuditStore(sessao), acao="unidade.atualizada", ator=Ator())

    async with sessoes() as sessao:
        validada = await sessao.scalar(
            text(
                "SELECT convalidated FROM pg_constraint"
                " WHERE conname = 'ck_audit_log_origem_obrigatoria'"
            )
        )
    assert validada is False
    assert await _trilha(sessoes) == []


async def test_linhas_antigas_continuam_aceitas(banco_vazio: BancoDeTeste) -> None:
    """013/R1.5, R1.6: eventos de antes da 013, com tipo e resultado nulos, continuam no banco,
    consultáveis e íntegros depois da 0013_02; eventos novos encadeiam neles."""
    await _migrar(banco_vazio.url_dono, "0011_09")
    engine = motor(banco_vazio.url_api)
    sessoes = async_sessionmaker(engine, expire_on_commit=False)
    antigo = await _registrar_como_antes_da_013(sessoes, "unidade.criada")

    await _migrar(banco_vazio.url_dono, "head")
    async with sessoes() as sessao, sessao.begin():
        await registrar(
            SqlAuditStore(sessao),
            acao="unidade.atualizada",
            ator=Ator(tipo="sistema", origem="teste"),
        )
    trilha = await _trilha(sessoes)
    cabeca = await _cabeca(sessoes)
    await engine.dispose()

    assert trilha[0]["hash"] == antigo.hash
    assert (trilha[0]["actor_type"], trilha[0]["result"]) == (None, None)
    assert (trilha[1]["actor_type"], trilha[1]["result"]) == ("sistema", "success")
    _assert_cadeia_integra(trilha, cabeca)
