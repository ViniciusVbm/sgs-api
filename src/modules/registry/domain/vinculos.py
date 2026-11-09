"""Equipamentos e serviços (spec 006, R5 e R6).

Um equipamento ou serviço pertence a uma unidade (`unit_id`) ou fica solto, sem unidade, como a
UTI móvel e a sala de vacinação do shopping (R5.2, R6.2). O vínculo é sempre pelo id (R6.4).
"""

from dataclasses import dataclass, fields
from datetime import datetime
from uuid import UUID

STATUS_DO_EQUIPAMENTO = ("ativo", "inativo", "em_manutencao")
STATUS_DO_SERVICO = ("ativo", "inativo")


@dataclass(frozen=True, slots=True, kw_only=True)
class DadosDoEquipamento:
    """Campos de negócio do equipamento, com os nomes das colunas de `equipments`."""

    name: str
    equipment_type_code: str
    quantity: int
    status: str
    cnes: str | None = None


CAMPOS_DO_EQUIPAMENTO = tuple(campo.name for campo in fields(DadosDoEquipamento))


@dataclass(frozen=True, slots=True, kw_only=True)
class Equipamento(DadosDoEquipamento):
    id: UUID
    unit_id: UUID | None
    created_at: datetime
    updated_at: datetime

    def campos_de_negocio(self) -> dict[str, object]:
        return {campo: getattr(self, campo) for campo in CAMPOS_DO_EQUIPAMENTO}


@dataclass(frozen=True, slots=True, kw_only=True)
class DadosDoServico:
    """Campos de negócio do serviço, com os nomes das colunas de `services`."""

    name: str
    service_type_id: int
    in_cnes: bool
    status: str
    equipment_id: UUID | None = None


CAMPOS_DO_SERVICO = tuple(campo.name for campo in fields(DadosDoServico))


@dataclass(frozen=True, slots=True, kw_only=True)
class Servico(DadosDoServico):
    id: UUID
    unit_id: UUID | None
    created_at: datetime
    updated_at: datetime

    def campos_de_negocio(self) -> dict[str, object]:
        return {campo: getattr(self, campo) for campo in CAMPOS_DO_SERVICO}
