"""Erros do banco não levam os valores da consulta para a exceção nem para o log (001/R4.3)."""

from typing import Any

import pytest
import structlog
from sqlalchemy import TextClause, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from src.core.db import create_engine
from src.core.ids import uuid7
from src.core.logging import configure_logging
from tests.factories import ARGON2ID_DE_TESTE, make_settings
from tests.integration.postgres import BancoDeTeste

VALOR_SENSIVEL = "f" * 64  # faz o papel de um hash ou segredo gravado pela aplicação

INSERIR_USUARIO = text(
    "INSERT INTO users (id, username, display_name, source, password_hash, email, mfa_enabled)"
    " VALUES (:id, :username, 'Teste', 'local', :senha, :email, :mfa)"
)
EMAIL = "maria.silva@example.org"
SAL_DO_HASH = ARGON2ID_DE_TESTE.split("$")[4]

Comando = tuple[TextClause, dict[str, Any]]


def _usuario(**valores: Any) -> dict[str, Any]:
    padrao = {"username": "maria.silva", "senha": ARGON2ID_DE_TESTE, "email": None, "mfa": False}
    return {"id": uuid7()} | padrao | valores


@pytest.mark.parametrize("pooled", [True, False], ids=["com-pool", "sem-pool"])
async def test_erro_do_banco_nao_mostra_os_parametros(banco: BancoDeTeste, pooled: bool) -> None:
    """001/R4.3"""
    engine = create_engine(banco.url_dono, make_settings(), pooled=pooled)
    try:
        with pytest.raises(IntegrityError) as erro:
            async with engine.begin() as conexao:
                # A linha 1 já existe: a chave primária recusa a segunda.
                await conexao.execute(
                    text("INSERT INTO audit_chain_head (id, last_hash) VALUES (1, :valor)"),
                    {"valor": VALOR_SENSIVEL},
                )
    finally:
        await engine.dispose()

    assert "pk_audit_chain_head" in str(erro.value)
    assert VALOR_SENSIVEL not in str(erro.value)


@pytest.mark.parametrize(
    ("preparo", "falha", "segredo", "pista"),
    [
        # CHECK: o DETAIL repete a linha recusada, com o hash da senha.
        ([], (INSERIR_USUARIO, _usuario(mfa=True)), SAL_DO_HASH, "ck_users_mfa_com_segredo"),
        # UNIQUE: o DETAIL repete o valor duplicado.
        (
            [(INSERIR_USUARIO, _usuario(email=EMAIL))],
            (INSERIR_USUARIO, _usuario(username="outra", email=EMAIL)),
            EMAIL,
            "uq_users_email",
        ),
        # Tipo errado: o asyncpg recusa antes de enviar e repete o valor na mensagem.
        (
            [],
            (text("UPDATE users SET failed_logins = :valor"), {"valor": VALOR_SENSIVEL}),
            VALOR_SENSIVEL,
            "invalid input for query argument $1",
        ),
    ],
    ids=["check", "unique", "argumento"],
)
async def test_log_do_erro_do_banco_nao_mostra_os_valores_recusados(
    banco: BancoDeTeste,
    capsys: pytest.CaptureFixture[str],
    preparo: list[Comando],
    falha: Comando,
    segredo: str,
    pista: str,
) -> None:
    """001/R4.3: o log do erro inesperado (request_context) mantém a pista e perde o valor."""
    configure_logging("INFO")
    engine = create_engine(banco.url_api, make_settings())
    try:
        async with engine.begin() as conexao:
            for comando, valores in preparo:
                await conexao.execute(comando, valores)
        with pytest.raises(DBAPIError) as erro:
            async with engine.begin() as conexao:
                await conexao.execute(*falha)
    finally:
        await engine.dispose()

    structlog.get_logger().error("erro_inesperado", exc_info=erro.value)

    saida = capsys.readouterr().out
    assert pista in saida
    assert segredo not in saida
