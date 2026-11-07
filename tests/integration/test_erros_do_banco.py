"""Erros do banco não levam os valores da consulta para a exceção nem para o log (001/R4.3)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.core.db import create_engine
from tests.factories import make_settings
from tests.integration.postgres import BancoDeTeste

VALOR_SENSIVEL = "f" * 64  # faz o papel de um hash ou segredo gravado pela aplicação


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
