"""`sgs-admin auditoria ancorar` (spec 013, T9; R5.4, R5.9).

O `main` roda numa thread (ele abre o próprio laço de eventos), lendo a configuração do ambiente.
"""

import asyncio
import json
import re

import pytest

from src.tools.sgs_admin import main
from tests.integration.postgres import BancoDeTeste
from tests.integration.tools.apoio_auditoria import (
    configurar_ambiente,
    estado_da_trilha,
    gravar_eventos,
)


@pytest.fixture
def ambiente(monkeypatch: pytest.MonkeyPatch, banco: BancoDeTeste) -> BancoDeTeste:
    configurar_ambiente(monkeypatch, banco)
    return banco


async def test_ancorar_emite_json_sem_gravar(
    ambiente: BancoDeTeste, capsys: pytest.CaptureFixture[str]
) -> None:
    """013/R5.4, R5.9: uma linha JSON com versão, cadeia, id, hash, total, instante e banco, sem
    dado pessoal; a trilha e a cabeça não mudam."""
    await gravar_eventos(ambiente, 3)
    antes = await estado_da_trilha(ambiente)

    codigo = await asyncio.to_thread(main, ["auditoria", "ancorar"])

    saida = capsys.readouterr()
    assert codigo == 0, saida.err
    ancora = json.loads(saida.out)
    assert set(ancora) == {"versao", "cadeia_id", "id", "hash", "total", "instante", "banco"}
    assert ancora["versao"] == 1
    assert ancora["total"] == 3
    assert ancora["hash"] == antes[1]  # o último evento é a cabeça
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z", ancora["instante"])
    assert await estado_da_trilha(ambiente) == antes


async def test_ancorar_identifica_a_cadeia(
    ambiente: BancoDeTeste, capsys: pytest.CaptureFixture[str]
) -> None:
    """013/R5.4: `cadeia_id` é o hash do primeiro evento e não muda com eventos novos; a âncora
    nova aponta o último."""
    await gravar_eventos(ambiente, 2)
    await asyncio.to_thread(main, ["auditoria", "ancorar"])
    primeira = json.loads(capsys.readouterr().out)
    await gravar_eventos(ambiente, 2)

    await asyncio.to_thread(main, ["auditoria", "ancorar"])

    segunda = json.loads(capsys.readouterr().out)
    _, _, primeiro_hash = await estado_da_trilha(ambiente)
    assert primeira["cadeia_id"] == segunda["cadeia_id"] == primeiro_hash
    assert segunda["id"] > primeira["id"]
    assert (primeira["total"], segunda["total"]) == (2, 4)


async def test_cadeia_vazia_nao_emite_ancora(
    ambiente: BancoDeTeste, capsys: pytest.CaptureFixture[str]
) -> None:
    """013/R5.4: sem eventos, não há âncora: código 2 e o motivo na saída de erro."""
    codigo = await asyncio.to_thread(main, ["auditoria", "ancorar"])

    saida = capsys.readouterr()
    assert codigo == 2
    assert saida.out == ""
    assert "cadeia vazia: nada a ancorar" in saida.err
