"""Schemas de saída da trilha e do log do banco. Datas no fuso de Recife (008/R1.2)."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.core.fuso import em_recife
from src.modules.audit.application.consultar import (
    Evento,
    Particao,
    RegistroDoBanco,
    ResultadoDaVerificacao,
    rotulo,
)


class AutorOut(BaseModel):
    id: UUID | None
    nome: str | None
    papeis: list[str]


class MudancaOut(BaseModel):
    campo: str
    rotulo: str
    de: Any
    para: Any


def _mudancas(changes: tuple[Mapping[str, object], ...]) -> list[MudancaOut]:
    return [
        MudancaOut(
            campo=str(m.get("campo")),
            rotulo=rotulo(str(m.get("campo"))),
            de=m.get("de"),
            para=m.get("para"),
        )
        for m in changes
    ]


class EventoOut(BaseModel):
    """Um evento da trilha (008/R1.2, R2.1)."""

    id: int
    quando: datetime
    acao: str
    autor: AutorOut
    entidade_tipo: str | None
    entidade_id: str | None
    mudancas: list[MudancaOut]
    metadados: dict[str, Any]

    @classmethod
    def de(cls, evento: Evento) -> Self:
        return cls(
            id=evento.id,
            quando=em_recife(evento.occurred_at),
            acao=evento.action,
            autor=AutorOut(
                id=evento.actor_user_id, nome=evento.actor_name, papeis=list(evento.actor_roles)
            ),
            entidade_tipo=evento.entity_type,
            entidade_id=evento.entity_id,
            mudancas=_mudancas(evento.changes),
            metadados=dict(evento.metadata),
        )


class EventoDetalheOut(EventoOut):
    """008/R3.2: com a cadeia de hash e a origem."""

    sessao_id: UUID | None
    ip: str | None
    request_id: str | None
    prev_hash: str | None
    hash: str | None

    @classmethod
    def do_evento(cls, evento: Evento) -> Self:
        return cls(
            **EventoOut.de(evento).model_dump(),
            sessao_id=evento.session_id,
            ip=evento.ip,
            request_id=evento.request_id,
            prev_hash=evento.prev_hash,
            hash=evento.hash,
        )


class VerificacaoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    de: datetime | None = Field(default=None, description="Início do período (inclusive).")
    ate: datetime | None = Field(default=None, description="Fim do período (exclusivo).")


class VerificacaoOut(BaseModel):
    integra: bool
    verificados: int
    primeiro_evento_divergente: int | None
    motivo: str | None

    @classmethod
    def de(cls, resultado: ResultadoDaVerificacao) -> Self:
        return cls(
            integra=resultado.integra,
            verificados=resultado.verificados,
            primeiro_evento_divergente=resultado.primeiro_evento_divergente,
            motivo=resultado.motivo,
        )


class RegistroDoBancoOut(BaseModel):
    id: int
    quando: datetime
    tabela: str
    operacao: str
    linha_id: UUID
    colunas: dict[str, Any]
    usuario_do_banco: str
    pela_api: bool

    @classmethod
    def de(cls, registro: RegistroDoBanco) -> Self:
        return cls(
            id=registro.id,
            quando=em_recife(registro.occurred_at),
            tabela=registro.table_name,
            operacao=registro.operation,
            linha_id=registro.row_id,
            colunas=dict(registro.changed_columns),
            usuario_do_banco=registro.db_user,
            pela_api=registro.via_api,
        )


class ParticaoOut(BaseModel):
    nome: str
    limite: str
    linhas: int

    @classmethod
    def de(cls, particao: Particao) -> Self:
        return cls(nome=particao.nome, limite=particao.limite, linhas=particao.linhas)
