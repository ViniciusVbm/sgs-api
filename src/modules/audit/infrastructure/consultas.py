"""Consultas da trilha e do log do banco em SQL escrito à mão (ADR-0009; spec 008; 011/T15)."""

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, TextClause
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.sql import consulta
from src.modules.audit.domain.consultas import (
    Evento,
    FiltrosDeEventos,
    FiltrosDeHistorico,
    FiltrosDoLogDoBanco,
    Pagina,
    Particao,
    RegistroDoBanco,
    Resultado,
)
from src.modules.audit.domain.entry import Ator, AuditEntry, Entidade, Mudanca

_SQL = Path(__file__).parent / "sql"

_HISTORICO = consulta(_SQL / "unit_history.sql")
_EVENTOS = consulta(_SQL / "audit_events.sql")
_EVENTO = consulta(_SQL / "audit_event_by_id.sql")
_LOTE = consulta(_SQL / "audit_chain_batch.sql")
_HASH_ANTERIOR = consulta(_SQL / "audit_hash_before.sql")
_LOG_DO_BANCO = consulta(_SQL / "db_change_log_list.sql")
_PARTICOES = consulta(_SQL / "db_change_log_partitions.sql")


class SqlConsultasDeAuditoria:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def historico_da_unidade(
        self, unidade_id: UUID, filtros: FiltrosDeHistorico, pagina: Pagina
    ) -> Resultado[Evento]:
        parametros = {
            "unit_id": unidade_id,
            "de": filtros.de,
            "ate": filtros.ate,
            "autor": filtros.autor,
            "campo": filtros.campo,
        }
        linhas, total = await self._pagina(_HISTORICO, parametros, pagina)
        return Resultado(
            itens=tuple(
                _evento(
                    linha,
                    id_=linha["audit_id"],
                    entidade=("unidade", str(unidade_id)),
                )
                for linha in linhas
            ),
            total=total,
        )

    async def eventos(
        self, filtros: FiltrosDeEventos, pagina: Pagina, *, incluir_acessos: bool
    ) -> Resultado[Evento]:
        parametros = {
            "de": filtros.de,
            "ate": filtros.ate,
            "acao": filtros.acao,
            "entidade_tipo": filtros.entidade_tipo,
            "entidade_id": filtros.entidade_id,
            "autor": filtros.autor,
            "incluir_acessos": incluir_acessos,
        }
        linhas, total = await self._pagina(_EVENTOS, parametros, pagina)
        return Resultado(itens=tuple(_evento(linha) for linha in linhas), total=total)

    async def evento(self, id_: int) -> Evento | None:
        linha = (await self._session.execute(_EVENTO, {"id": id_})).mappings().one_or_none()
        return None if linha is None else _evento(linha)

    async def lote_da_cadeia(
        self, depois_de: int, de: datetime | None, ate: datetime | None, limite: int
    ) -> list[tuple[int, AuditEntry]]:
        resultado = await self._session.execute(
            _LOTE, {"depois_de": depois_de, "de": de, "ate": ate, "limit": limite}
        )
        return [(int(linha["id"]), _entrada(linha)) for linha in resultado.mappings()]

    async def hash_anterior(self, id_: int) -> str | None:
        valor: str | None = await self._session.scalar(_HASH_ANTERIOR, {"id": id_})
        return valor

    async def log_do_banco(
        self, filtros: FiltrosDoLogDoBanco, pagina: Pagina
    ) -> Resultado[RegistroDoBanco]:
        parametros = {
            "de": filtros.de,
            "ate": filtros.ate,
            "tabela": filtros.tabela,
            "fora_da_api": filtros.fora_da_api,
        }
        linhas, total = await self._pagina(_LOG_DO_BANCO, parametros, pagina)
        return Resultado(
            itens=tuple(
                RegistroDoBanco(**{c: v for c, v in linha.items() if c != "total"})
                for linha in linhas
            ),
            total=total,
        )

    async def particoes(self) -> list[Particao]:
        resultado = await self._session.execute(_PARTICOES)
        return [
            Particao(nome=linha["name"], limite=linha["bound"], linhas=int(linha["row_count"]))
            for linha in resultado.mappings()
        ]

    async def _pagina(
        self, consulta_: TextClause, parametros: dict[str, Any], pagina: Pagina
    ) -> tuple[list[RowMapping], int]:
        completos = {**parametros, "limit": pagina.tamanho, "offset": pagina.offset}
        linhas = list((await self._session.execute(consulta_, completos)).mappings())
        if linhas:
            return linhas, int(linhas[0]["total"])
        if pagina.offset == 0:
            return [], 0
        primeira = await self._session.execute(consulta_, {**completos, "limit": 1, "offset": 0})
        contagem = primeira.mappings().first()
        return [], 0 if contagem is None else int(contagem["total"])


def _evento(
    linha: RowMapping, *, id_: int | None = None, entidade: tuple[str, str] | None = None
) -> Evento:
    tipo, ident = entidade if entidade else (linha.get("entity_type"), linha.get("entity_id"))
    return Evento(
        id=int(id_ if id_ is not None else linha["id"]),
        occurred_at=linha["occurred_at"],
        action=linha["action"],
        actor_user_id=linha["actor_user_id"],
        actor_name=linha.get("actor_name"),
        actor_roles=tuple(linha["actor_roles"] or ()),
        entity_type=tipo,
        entity_id=ident,
        changes=tuple(linha["changes"] or ()),
        metadata=dict(linha["metadata"] or {}),
        session_id=linha.get("session_id"),
        ip=linha.get("ip"),
        request_id=linha.get("request_id"),
        prev_hash=linha.get("prev_hash"),
        hash=linha.get("hash"),
    )


def _entrada(linha: RowMapping) -> AuditEntry:
    """O registro como `AuditEntry`, para recalcular o hash com a mesma canonização da gravação."""
    entidade = (
        None
        if linha["entity_type"] is None
        else Entidade(tipo=linha["entity_type"], id=linha["entity_id"])
    )
    return AuditEntry(
        occurred_at=linha["occurred_at"],
        action=linha["action"],
        actor=Ator(
            user_id=linha["actor_user_id"],
            papeis=tuple(linha["actor_roles"] or ()),
            session_id=linha["session_id"],
            ip=linha["ip"],
            request_id=linha["request_id"],
        ),
        entity=entidade,
        changes=tuple(
            Mudanca(campo=m["campo"], de=m.get("de"), para=m.get("para"))
            for m in (linha["changes"] or ())
        ),
        metadata=dict(linha["metadata"] or {}),
        prev_hash=linha["prev_hash"],
        hash=linha["hash"],
    )
