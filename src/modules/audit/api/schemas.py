"""Schemas de saída da trilha e do log do banco. Datas no fuso de Recife (008/R1.2)."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.core.fuso import em_recife
from src.modules.audit.application.consultar import (
    Ancora,
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
    tipo: str | None = Field(
        description="usuario, anonimo, sistema, servico, seed ou cli_admin; null antes da 013."
    )


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
    origem: str | None = Field(description="Rótulo de origem (api, seed...); null antes da 013.")
    resultado: str | None = Field(description="success, failure ou denied; null antes da 013.")
    resultado_categoria: str | None

    @classmethod
    def de(cls, evento: Evento) -> Self:
        return cls(
            id=evento.id,
            quando=em_recife(evento.occurred_at),
            acao=evento.action,
            autor=AutorOut(
                id=evento.actor_user_id,
                nome=evento.actor_name,
                papeis=list(evento.actor_roles),
                tipo=evento.actor_type,
            ),
            entidade_tipo=evento.entity_type,
            entidade_id=evento.entity_id,
            mudancas=_mudancas(evento.changes),
            metadados=dict(evento.metadata),
            origem=evento.origin,
            resultado=evento.result,
            resultado_categoria=evento.result_reason,
        )


class EventoDetalheOut(EventoOut):
    """008/R3.2: com a cadeia de hash e a origem. 013/R8.2: IP, User-Agent e sessão só com
    `auditoria:read_acessos`; sem ela vêm nulos e `origem_restrita` é verdadeiro."""

    sessao_id: UUID | None
    ip: str | None
    user_agent: str | None
    origem_restrita: bool
    request_id: str | None
    prev_hash: str | None
    hash: str | None

    @classmethod
    def do_evento(cls, evento: Evento) -> Self:
        return cls(
            **EventoOut.de(evento).model_dump(),
            sessao_id=evento.session_id,
            ip=evento.ip,
            user_agent=evento.user_agent,
            origem_restrita=evento.origem_restrita,
            request_id=evento.request_id,
            prev_hash=evento.prev_hash,
            hash=evento.hash,
        )


_HASH = r"^[0-9a-f]{64}$"


class AncoraIn(BaseModel):
    """013/R5.3: a âncora guardada fora do banco (gerada por `sgs-admin auditoria ancorar`)."""

    model_config = ConfigDict(extra="forbid")

    cadeia_id: str = Field(pattern=_HASH, description="Hash do primeiro evento da cadeia.")
    id: int = Field(ge=1, description="Evento ancorado.")
    hash: str = Field(pattern=_HASH, description="Hash que o evento ancorado tinha.")

    def para_dominio(self) -> Ancora:
        return Ancora(cadeia_id=self.cadeia_id, id=self.id, hash=self.hash)


class VerificacaoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    de: datetime | None = Field(default=None, description="Início do período (inclusive).")
    ate: datetime | None = Field(default=None, description="Fim do período (exclusivo).")
    ancora: AncoraIn | None = Field(default=None, description="Âncora externa (013/R5.3).")


class VerificacaoOut(BaseModel):
    integra: bool
    verificados: int
    primeiro_evento_divergente: int | None
    motivo: str | None
    ultimo_id: int | None = Field(description="Último evento conferido (013/R5.5).")
    hash_final: str | None = Field(description="Hash do último evento conferido (013/R5.5).")
    cabeca_confere: bool | None = Field(
        description="Se o fim da cadeia bate com `audit_chain_head`; `null` com período (013/R5.1)."
    )
    cadeia_confere: bool | None = Field(
        description="Se a cadeia é a da âncora; `null` sem âncora (013/R5.3)."
    )
    ancora_confere: bool | None = Field(
        description="Se o evento ancorado ainda tem o hash da âncora; `null` sem âncora (013/R5.3)."
    )

    @classmethod
    def de(cls, resultado: ResultadoDaVerificacao) -> Self:
        return cls(
            integra=resultado.integra,
            verificados=resultado.verificados,
            primeiro_evento_divergente=resultado.primeiro_evento_divergente,
            motivo=resultado.motivo,
            ultimo_id=resultado.ultimo_id,
            hash_final=resultado.hash_final,
            cabeca_confere=resultado.cabeca_confere,
            cadeia_confere=resultado.cadeia_confere,
            ancora_confere=resultado.ancora_confere,
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
