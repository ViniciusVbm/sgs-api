"""Consulta da trilha de auditoria e do log do banco (spec 008; spec 011, R7 e T15).

Valores que entram e saem da porta `ConsultasDeAuditoria`, sem banco nem HTTP.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

ROTULOS_CAMPOS: Mapping[str, str] = {
    "name": "Nome",
    "cnes": "CNES",
    "unit_type_id": "Tipo de unidade",
    "district_id": "Distrito sanitário",
    "cep": "CEP",
    "address": "Endereço",
    "neighborhood": "Bairro",
    "phone": "Telefone",
    "manager_name": "Nome do gestor",
    "opening_hours": "Horário de funcionamento",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "status": "Status",
    "equipment_type_code": "Tipo de equipamento",
    "quantity": "Quantidade",
    "service_type_id": "Tipo de serviço",
    "in_cnes": "Consta no CNES",
    "equipment_id": "Equipamento",
    "code": "Código",
    "is_active": "Ativo",
    "technical_area_id": "Área técnica",
}
"""Campo (nome da coluna, como a trilha grava) → rótulo legível (008/R1.2; design § Consulta)."""


def rotulo(campo: str) -> str:
    return ROTULOS_CAMPOS.get(campo, campo)


@dataclass(frozen=True, slots=True)
class Pagina:
    numero: int
    tamanho: int

    @property
    def offset(self) -> int:
        return (self.numero - 1) * self.tamanho


@dataclass(frozen=True, slots=True, kw_only=True)
class FiltrosDeHistorico:
    """008/R1.3: período, autor e campo."""

    de: datetime | None = None
    ate: datetime | None = None
    autor: UUID | None = None
    campo: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FiltrosDeEventos:
    """008/R2.1: período, ação (prefixo), entidade e autor."""

    de: datetime | None = None
    ate: datetime | None = None
    acao: str | None = None
    entidade_tipo: str | None = None
    entidade_id: str | None = None
    autor: UUID | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FiltrosDoLogDoBanco:
    """011/R7.7: período, tabela e só o que foi feito fora da API."""

    de: datetime | None = None
    ate: datetime | None = None
    tabela: str | None = None
    fora_da_api: bool = False


@dataclass(frozen=True, slots=True)
class Resultado[T]:
    itens: tuple[T, ...]
    total: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Evento:
    """Um registro da trilha, como a consulta o devolve."""

    id: int
    occurred_at: datetime
    action: str
    actor_user_id: UUID | None
    actor_name: str | None
    actor_roles: tuple[str, ...]
    entity_type: str | None
    entity_id: str | None
    changes: tuple[Mapping[str, object], ...]
    metadata: Mapping[str, object] = field(default_factory=dict)
    session_id: UUID | None = None
    ip: str | None = None
    request_id: str | None = None
    prev_hash: str | None = None
    hash: str | None = None
    # Spec 013: nulos nos eventos anteriores a ela (R1.5). `user_agent` só sai no detalhe.
    actor_type: str | None = None
    origin: str | None = None
    user_agent: str | None = None
    result: str | None = None
    result_reason: str | None = None
    origem_restrita: bool = False


@dataclass(frozen=True, slots=True)
class ResultadoDaVerificacao:
    """008/R3.1: `integra`, quantos eventos foram conferidos e, se quebrou, onde. 013/R5.5: o
    último evento conferido, o hash dele e se o fim da cadeia bate com `audit_chain_head`
    (`None` quando a verificação é de um período, que não chega ao fim da cadeia)."""

    integra: bool
    verificados: int
    primeiro_evento_divergente: int | None = None
    motivo: str | None = None
    ultimo_id: int | None = None
    hash_final: str | None = None
    cabeca_confere: bool | None = None
    cadeia_confere: bool | None = None
    ancora_confere: bool | None = None


@dataclass(frozen=True, slots=True)
class Ancora:
    """013/R5.3: a referência guardada fora do banco: a cadeia (hash do primeiro evento) e um
    evento dela com o hash que ele tinha."""

    cadeia_id: str
    id: int
    hash: str


@dataclass(frozen=True, slots=True)
class IdentidadeDaCadeia:
    """013/R5.4: hash do primeiro evento (`None` se a cadeia está vazia), total e nome do banco."""

    cadeia_id: str | None
    total: int
    banco: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistroDoBanco:
    id: int
    occurred_at: datetime
    table_name: str
    operation: str
    row_id: UUID
    changed_columns: Mapping[str, object]
    db_user: str
    via_api: bool


@dataclass(frozen=True, slots=True)
class Particao:
    nome: str
    limite: str
    linhas: int
