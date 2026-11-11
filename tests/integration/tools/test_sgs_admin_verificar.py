"""`sgs-admin auditoria verificar [--ancora arquivo.json]` (spec 013, T9; R5.12).

A mesma verificação da API, direto no banco, sem a API e sem gravar nada.
"""

import asyncio
import json
from pathlib import Path

import pytest

from src.tools.sgs_admin import main
from tests.integration.postgres import BancoDeTeste
from tests.integration.tools.apoio_auditoria import (
    adulterar,
    configurar_ambiente,
    estado_da_trilha,
    gravar_eventos,
)


@pytest.fixture
def ambiente(monkeypatch: pytest.MonkeyPatch, banco: BancoDeTeste) -> BancoDeTeste:
    configurar_ambiente(monkeypatch, banco)
    return banco


async def _ancorar(capsys: pytest.CaptureFixture[str], destino: Path) -> Path:
    assert await asyncio.to_thread(main, ["auditoria", "ancorar"]) == 0
    await asyncio.to_thread(destino.write_text, capsys.readouterr().out, encoding="utf-8")
    return destino


async def test_verificar_offline_integra_com_codigo_zero(
    ambiente: BancoDeTeste, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """013/R5.12: cadeia íntegra, com e sem âncora: código 0 e o resultado em JSON."""
    await gravar_eventos(ambiente, 3)
    ancora = await _ancorar(capsys, tmp_path / "ancora.json")
    await gravar_eventos(ambiente, 1)  # a âncora antiga continua valendo

    sem = await asyncio.to_thread(main, ["auditoria", "verificar"])
    sem_saida = json.loads(capsys.readouterr().out)
    com = await asyncio.to_thread(main, ["auditoria", "verificar", "--ancora", str(ancora)])
    com_saida = json.loads(capsys.readouterr().out)

    assert (sem, com) == (0, 0)
    assert (sem_saida["integra"], sem_saida["verificados"], sem_saida["cabeca_confere"]) == (
        True,
        4,
        True,
    )
    assert sem_saida["ancora_confere"] is None
    assert (com_saida["integra"], com_saida["cadeia_confere"], com_saida["ancora_confere"]) == (
        True,
        True,
        True,
    )


async def test_verificar_offline_acusa_adulteracao_com_codigo_um(
    ambiente: BancoDeTeste, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """013/R5.12: adulteração (metadados alterados como superusuário) dá código 1 e aponta o
    evento, também com a âncora."""
    await gravar_eventos(ambiente, 3)
    ancora = await _ancorar(capsys, tmp_path / "ancora.json")
    await adulterar(
        ambiente,
        "UPDATE audit_log SET metadata = '{}' WHERE id = (SELECT min(id) + 1 FROM audit_log)",
    )

    codigo = await asyncio.to_thread(main, ["auditoria", "verificar", "--ancora", str(ancora)])

    saida = json.loads(capsys.readouterr().out)
    assert codigo == 1
    assert saida["integra"] is False
    assert saida["motivo"] == "o conteúdo não confere com o hash gravado"
    assert saida["primeiro_evento_divergente"] is not None


async def test_verificar_offline_nao_grava_nada(
    ambiente: BancoDeTeste, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """013/R5.12: nem `auditoria.verificada`, nem nada mais: total e cabeça iguais."""
    await gravar_eventos(ambiente, 3)
    ancora = await _ancorar(capsys, tmp_path / "ancora.json")
    antes = await estado_da_trilha(ambiente)

    await asyncio.to_thread(main, ["auditoria", "verificar"])
    await asyncio.to_thread(main, ["auditoria", "verificar", "--ancora", str(ancora)])

    capsys.readouterr()
    assert await estado_da_trilha(ambiente) == antes


@pytest.mark.parametrize(
    "conteudo",
    [
        "isto não é json",
        json.dumps({"versao": 2, "cadeia_id": "a" * 64, "id": 1, "hash": "b" * 64}),
        json.dumps({"versao": 1, "cadeia_id": "xyz", "id": 1, "hash": "b" * 64}),
        json.dumps({"versao": 1, "cadeia_id": "a" * 64, "id": 0, "hash": "b" * 64}),
        json.dumps({"versao": 1, "cadeia_id": "a" * 64, "id": 1}),
        None,
    ],
    ids=["nao_json", "versao", "cadeia_id", "id", "sem_hash", "arquivo_inexistente"],
)
async def test_verificar_offline_com_ancora_invalida_da_codigo_dois(
    ambiente: BancoDeTeste,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    conteudo: str | None,
) -> None:
    """013/R5.12: âncora ilegível, de outra versão ou com campo inválido: código 2, sem
    verificar."""
    await gravar_eventos(ambiente, 1)
    arquivo = tmp_path / "ancora.json"
    if conteudo is not None:
        await asyncio.to_thread(arquivo.write_text, conteudo, encoding="utf-8")

    codigo = await asyncio.to_thread(main, ["auditoria", "verificar", "--ancora", str(arquivo)])

    saida = capsys.readouterr()
    assert codigo == 2
    assert saida.out == ""
    assert saida.err.startswith("sgs-admin: ")
