"""Schemas de saída das consultas do dashboard (design da 011 § Rotas).

Lidos dos valores do domínio (`model_validate` com `from_attributes`), nunca de linhas do banco.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.modules.dashboard.application.consultas import SituacaoConciliacao


class UnidadeResumoOut(BaseModel):
    """Unidade numa consulta de qualidade; `tipo` e `distrito` são os nomes, para leitura."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nome: str
    cnes: str | None
    tipo: str
    distrito: str


class ConciliacaoOut(BaseModel):
    """Linha da conciliação unidade x equipamento; o lado que faltar vem nulo. `distrito` é o
    nome do distrito da unidade e `equipamento_tipo`, o nome do tipo do equipamento."""

    model_config = ConfigDict(from_attributes=True)

    unidade_id: UUID | None
    unidade_nome: str | None
    distrito: str | None
    equipamento_id: UUID | None
    equipamento_nome: str | None
    equipamento_tipo: str | None
    situacao: SituacaoConciliacao


class _DaLinha(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class DistritoSemCnesOut(_DaLinha):
    district_id: int
    district_name: str
    total_units: int
    units_without_cnes: int
    percent_without_cnes: float
    network_percent_without_cnes: float


class UnidadeForaDoCnesOut(_DaLinha):
    unit_id: UUID
    name: str
    cnes: str | None
    unit_type_name: str
    district_name: str
    services_outside_cnes_count: int


class InventarioOut(_DaLinha):
    """Linha da `vw_unit_inventory` (011/R4.1); sem dado pessoal (R4.2)."""

    unit_id: UUID
    name: str
    cnes: str | None
    status: str
    registration_status: str
    unit_type_id: int
    unit_type_name: str
    technical_area_id: int
    technical_area_name: str
    district_id: int
    district_name: str
    equipment_count: int
    service_count: int
    services_outside_cnes_count: int


class CategoriaOut(_DaLinha):
    categoria: str
    chave: str
    rotulo: str
    quantidade: int


class EquipamentosPorTipoOut(_DaLinha):
    equipment_type_code: str
    equipment_type_name: str
    district_id: int
    district_name: str
    equipment_count: int
    total_quantity: int


class AlteracoesPorPeriodoOut(_DaLinha):
    district_id: int
    district_name: str
    last_7_days: int
    last_30_days: int


class AlteracaoRecenteOut(_DaLinha):
    audit_id: int
    occurred_at: datetime
    action: str
    unit_id: UUID
    unit_name: str
    district_name: str
    actor_name: str | None


class ItemDistribuicaoOut(BaseModel):
    chave: str
    rotulo: str
    quantidade: int


class UnidadesResumoOut(BaseModel):
    total: int
    por_status: dict[str, int]
    por_tipo: list[ItemDistribuicaoOut]
    por_area: list[ItemDistribuicaoOut]
    por_distrito: list[ItemDistribuicaoOut]
    por_situacao_cadastral: dict[str, int]


class QualidadeOut(BaseModel):
    unidades_com_pendencias: int
    total_pendencias: int
    sem_cnes: int
    servicos_fora_cnes: int


class AlteracoesResumoOut(BaseModel):
    ultimos_7_dias: int
    ultimos_30_dias: int
    recentes: list[AlteracaoRecenteOut]


class ResumoOut(BaseModel):
    """009/design § Resposta: unidades, qualidade e alterações, com a hora de Recife."""

    unidades: UnidadesResumoOut
    qualidade: QualidadeOut
    alteracoes: AlteracoesResumoOut
    gerado_em: datetime


class EntradaDoCatalogoOut(BaseModel):
    """011/R3.1: o que cada consulta mostra, sem o SQL."""

    model_config = ConfigDict(from_attributes=True)

    nome: str
    rota: str
    titulo: str
    justificativa: str
    tecnica_sql: str
    parametros: list[str]
    colunas: list[str]
    permissao: str
    grafico_sugerido: str
    paginada: bool
