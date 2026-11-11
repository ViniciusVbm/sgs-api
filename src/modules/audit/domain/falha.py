"""Metadados do evento `operacao.falhou` (spec 013, T6; R4.4, R4.5).

Lista fechada: só método, rota declarada, status, código de uma lista fixa e nomes de campos. Nada
é montado a partir do texto da exceção, então valores enviados, mensagens livres, pilha e SQL não
têm por onde entrar.
"""

import re
from collections.abc import Iterable
from typing import Any

ACAO = "operacao.falhou"

METODOS_DE_ESCRITA = frozenset({"POST", "PUT", "PATCH", "DELETE"})

CODIGOS: dict[str, str] = {
    "conflito": "conflito",
    "precondicao_falhou": "precondicao",
    "precondicao_ausente": "precondicao",
    "validacao_dominio": "validacao",
    "erro_interno": "erro_interno",
}
"""Código do erro → categoria (`result_reason`), os únicos valores aceitos (013/R4.4, R4.1)."""

CAMPOS_MAX = 20
_CAMPO = re.compile(r"[A-Za-z0-9_.]{1,50}")
_ROTA = re.compile(r"/[A-Za-z0-9_/{}.-]{0,200}")


def metadados_de_falha(
    *, metodo: str, rota: str, status: int, codigo: str, campos: Iterable[str] = ()
) -> dict[str, Any]:
    """Os metadados do evento. Recusa método de leitura, código fora da lista e rota que não
    seja um template; descarta nomes de campo fora do formato e passa de 20."""
    if metodo not in METODOS_DE_ESCRITA:
        raise ValueError(f"operacao.falhou só para escrita, não {metodo}")
    if codigo not in CODIGOS:
        raise ValueError(f"código de falha fora da lista: {codigo}")
    if not _ROTA.fullmatch(rota):
        raise ValueError("rota precisa ser o template declarado")
    nomes = [c for c in campos if isinstance(c, str) and _CAMPO.fullmatch(c)][:CAMPOS_MAX]
    return {
        "metodo": metodo,
        "rota": rota,
        "status": int(status),
        "codigo": codigo,
        "campos": nomes,
    }


def categoria_de(codigo: str) -> str:
    return CODIGOS[codigo]
