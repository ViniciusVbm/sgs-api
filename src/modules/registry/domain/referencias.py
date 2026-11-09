"""Tabelas de referência do cadastro (spec 006, R7)."""

from dataclasses import dataclass
from enum import StrEnum


class TipoDeReferencia(StrEnum):
    """As referências expostas em `/referencias/{tipo}` (006/R7.1), com o nome da tabela."""

    DISTRITOS = "distritos"
    AREAS_TECNICAS = "areas-tecnicas"
    TIPOS_UNIDADE = "tipos-unidade"
    TIPOS_EQUIPAMENTO = "tipos-equipamento"
    TIPOS_SERVICO = "tipos-servico"

    @property
    def tabela(self) -> str:
        return _TABELAS[self]

    @property
    def tem_area(self) -> bool:
        """Só o tipo de unidade pertence a uma área técnica."""
        return self is TipoDeReferencia.TIPOS_UNIDADE


_TABELAS = {
    TipoDeReferencia.DISTRITOS: "districts",
    TipoDeReferencia.AREAS_TECNICAS: "technical_areas",
    TipoDeReferencia.TIPOS_UNIDADE: "unit_types",
    TipoDeReferencia.TIPOS_EQUIPAMENTO: "equipment_types",
    TipoDeReferencia.TIPOS_SERVICO: "service_types",
}


@dataclass(frozen=True, slots=True, kw_only=True)
class Referencia:
    id: int
    code: str
    name: str
    is_active: bool
    technical_area_id: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DadosDaReferencia:
    """Campos alteráveis: código, nome, ativo e, no tipo de unidade, a área técnica."""

    code: str | None = None
    name: str | None = None
    is_active: bool | None = None
    technical_area_id: int | None = None
