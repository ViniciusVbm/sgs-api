"""Portas do módulo de auditoria."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.audit.domain.consultas import (
    Evento,
    FiltrosDeEventos,
    FiltrosDeHistorico,
    FiltrosDoLogDoBanco,
    IdentidadeDaCadeia,
    Pagina,
    Particao,
    RegistroDoBanco,
    Resultado,
)
from src.modules.audit.domain.entry import AuditEntry


class AuditStore(Protocol):
    """Armazenamento da trilha, preso à transação do caso de uso que registra o evento."""

    async def lock_chain_head(self) -> str:
        """Trava a cabeça da cadeia até o fim da transação e devolve o hash do último registro."""
        ...

    async def append(self, entry: AuditEntry) -> None:
        """Insere o registro e move a cabeça da cadeia para o hash dele."""
        ...


class ConsultasDeAuditoria(Protocol):
    """Leitura da trilha e do log do banco (spec 008; 011/T15). Só leitura."""

    async def historico_da_unidade(
        self, unidade_id: UUID, filtros: FiltrosDeHistorico, pagina: Pagina
    ) -> Resultado[Evento]: ...

    async def eventos(
        self, filtros: FiltrosDeEventos, pagina: Pagina, *, incluir_acessos: bool
    ) -> Resultado[Evento]: ...

    async def evento(self, id_: int) -> Evento | None: ...

    async def lote_da_cadeia(
        self, depois_de: int, de: datetime | None, ate: datetime | None, limite: int
    ) -> list[tuple[int, AuditEntry]]:
        """Eventos em ordem de id, reconstruídos como `AuditEntry` (com o hash gravado)."""
        ...

    async def hash_anterior(self, id_: int) -> str | None: ...

    async def fixar_foto_consistente(self) -> None:
        """013/R5.11: a partir daqui, todas as leituras veem a mesma foto do banco (REPEATABLE
        READ, READ ONLY). Precisa ser a primeira leitura da transação."""
        ...

    async def cabeca_da_cadeia(self) -> str:
        """013/R5.1: o `last_hash` de `audit_chain_head`."""
        ...

    async def identidade_da_cadeia(self) -> IdentidadeDaCadeia:
        """013/R5.3, R5.4: `cadeia_id`, total de eventos e nome do banco."""
        ...

    async def hash_do_evento(self, id_: int) -> str | None:
        """013/R5.3: o hash gravado do evento `id_`, ou `None` se ele não existe."""
        ...

    async def log_do_banco(
        self, filtros: FiltrosDoLogDoBanco, pagina: Pagina
    ) -> Resultado[RegistroDoBanco]: ...

    async def particoes(self) -> list[Particao]: ...
