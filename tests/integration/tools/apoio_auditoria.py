"""Apoio aos testes dos comandos `sgs-admin auditoria` (spec 013, T9)."""

import base64
import json

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.modules.audit.application.registrar import Ator, registrar
from src.modules.audit.infrastructure.repository import SqlAuditStore
from tests.factories import make_jwt_private_keys
from tests.integration.postgres import BancoDeTeste, motor


def configurar_ambiente(monkeypatch: pytest.MonkeyPatch, banco: BancoDeTeste) -> None:
    """A configuração (`Settings`) do comando apontando para o banco do teste, com o login da API
    (DATABASE_URL), como em produção (o mesmo padrão de test_sgs_admin_particoes.py)."""
    for nome in ("JWT_PRIVATE_KEYS_FILE", "CRYPTO_KEYS_FILE", "DATABASE_SSL_ROOT_CERT"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.delenv("DATABASE_MIGRATION_URL", raising=False)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", banco.url_api)
    monkeypatch.setenv("DATABASE_SSL_MODE", "disable")
    monkeypatch.setenv("JWT_PRIVATE_KEYS", make_jwt_private_keys())
    monkeypatch.setenv("CRYPTO_KEYS", json.dumps({"1": base64.b64encode(bytes(32 * [7])).decode()}))
    monkeypatch.setenv("CRYPTO_ACTIVE_KEY", "1")


async def gravar_eventos(banco: BancoDeTeste, quantidade: int) -> None:
    engine = motor(banco.url_api)
    sessoes = async_sessionmaker(engine, expire_on_commit=False)
    for numero in range(quantidade):
        async with sessoes() as sessao, sessao.begin():
            await registrar(
                SqlAuditStore(sessao),
                acao="unidade.atualizada",
                ator=Ator(tipo="sistema", origem="teste"),
                metadados={"n": numero},
            )
    await engine.dispose()


async def estado_da_trilha(banco: BancoDeTeste) -> tuple[int, str, str | None]:
    """(total de eventos, cabeça, hash do primeiro evento)."""
    engine = motor(banco.url_api)
    async with engine.connect() as conexao:
        total = int(await conexao.scalar(text("SELECT count(*) FROM audit_log")) or 0)
        cabeca = str(await conexao.scalar(text("SELECT last_hash FROM audit_chain_head")))
        primeiro = await conexao.scalar(text("SELECT hash FROM audit_log ORDER BY id LIMIT 1"))
    await engine.dispose()
    return total, cabeca, primeiro


async def adulterar(banco: BancoDeTeste, sql: str) -> None:
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        await conexao.execute(text("ALTER TABLE audit_log DISABLE TRIGGER USER"))
        await conexao.execute(text(sql))
        await conexao.execute(text("ALTER TABLE audit_log ENABLE TRIGGER USER"))
    await engine.dispose()
