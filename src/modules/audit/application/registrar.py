"""Caso de uso `audit.registrar` (spec 001, R5.1 e R5.3).

Outros módulos chamam `registrar` dentro da própria transação, com um `AuditStore` ligado à
mesma sessão: se o caso de uso falhar, a auditoria é desfeita junto.
"""

from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from src.modules.audit.domain.entry import Ator, AuditEntry, Entidade, Mudanca
from src.modules.audit.domain.falha import ACAO as ACAO_DE_FALHA
from src.modules.audit.domain.falha import categoria_de, metadados_de_falha
from src.modules.audit.domain.ports import AuditStore

# Reexportados para os outros módulos, que só importam a camada application da auditoria.
__all__ = [
    "Ator",
    "AuditEntry",
    "AuditStore",
    "Entidade",
    "Mudanca",
    "registrar",
    "registrar_falha",
]


def _now() -> datetime:
    return datetime.now(UTC)


async def registrar(
    store: AuditStore,
    *,
    acao: str,
    ator: Ator,
    entidade: Entidade | None = None,
    mudancas: Sequence[Mudanca] = (),
    metadados: Mapping[str, Any] | None = None,
    resultado: str = "success",
    categoria: str | None = None,
    agora: Callable[[], datetime] = _now,
) -> AuditEntry:
    """Grava o evento encadeado ao último registro. A trava da cabeça da cadeia serializa
    transações simultâneas, então a cadeia nunca bifurca. `resultado` e `categoria` são o
    `result` e o `result_reason` da spec 013 (R4.1): sem indicação, o evento é `success`; falha e
    negação passam o resultado e a categoria explicitamente."""
    prev_hash = await store.lock_chain_head()
    entry = AuditEntry.create(
        prev_hash=prev_hash,
        occurred_at=agora(),
        action=acao,
        actor=ator,
        entity=entidade,
        changes=tuple(mudancas),
        metadata=metadados,
        result=resultado,
        result_reason=categoria,
    )
    await store.append(entry)
    return entry


async def registrar_falha(
    store: AuditStore,
    *,
    ator: Ator,
    metodo: str,
    rota: str,
    status: int,
    codigo: str,
    campos: Sequence[str] = (),
    entidade: Entidade | None = None,
) -> AuditEntry:
    """013/R4.3 a R4.5: `operacao.falhou` com `failure`, a categoria do código e os metadados da
    lista fechada. Quem chama grava numa transação própria, depois do rollback da operação."""
    return await registrar(
        store,
        acao=ACAO_DE_FALHA,
        ator=ator,
        entidade=entidade,
        metadados=metadados_de_falha(
            metodo=metodo, rota=rota, status=status, codigo=codigo, campos=campos
        ),
        resultado="failure",
        categoria=categoria_de(codigo),
    )
