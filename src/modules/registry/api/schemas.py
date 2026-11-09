"""Schemas de entrada e saída da unidade (design da 006 § Schemas).

O formato é conferido aqui (tamanhos, CNES com 7 dígitos, CEP com 8, status); as regras de
negócio ficam nos casos de uso. Os campos da API estão em português; os do domínio e do banco, em
inglês (`nome` ↔ `name`).
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal, Self, cast
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from src.modules.registry.application.referencias import DadosDaReferencia, Referencia
from src.modules.registry.application.unidades import DadosDaUnidade, DetalheDaUnidade, Unidade
from src.modules.registry.application.vinculos import (
    DadosDoEquipamento,
    DadosDoServico,
    Equipamento,
    Servico,
)

StatusDaUnidade = Literal["ativa", "inativa", "em_implantacao"]

# Ids das referências são `smallint` no banco.
_IdDeReferencia = Annotated[int, Field(ge=1, le=32767)]

# `[0-9]` e não `\d`, que no Pydantic também aceita dígitos de outros alfabetos.
_Cnes = Annotated[str, Field(pattern=r"^[0-9]{7}$", description="Sete dígitos.")]
_Cep = Annotated[
    str,
    Field(pattern=r"^[0-9]{5}-?[0-9]{3}$", description="Oito dígitos, com ou sem hífen."),
    # O banco guarda só os dígitos (`varchar(8)`).
    AfterValidator(lambda cep: cep.replace("-", "")),
]
_Telefone = Annotated[str, Field(min_length=1, max_length=20, pattern=r"^[0-9()+\- ]+$")]


class UnidadeCreate(BaseModel):
    """Unidade nova (006/R1.2: nome, tipo, distrito, endereço com CEP e status obrigatórios)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    cnes: _Cnes | None = Field(default=None, description="Sem CNES, a unidade fica pendente.")
    tipo_unidade_id: _IdDeReferencia
    distrito_id: _IdDeReferencia
    cep: _Cep
    endereco: str = Field(min_length=1, max_length=200)
    bairro: str | None = Field(default=None, min_length=1, max_length=100)
    telefone: _Telefone | None = None
    nome_gestor: str | None = Field(default=None, min_length=1, max_length=150)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_digits=9, decimal_places=6)
    status: StatusDaUnidade

    def dados(self) -> DadosDaUnidade:
        return DadosDaUnidade(
            name=self.nome,
            cnes=self.cnes,
            unit_type_id=self.tipo_unidade_id,
            district_id=self.distrito_id,
            cep=self.cep,
            address=self.endereco,
            neighborhood=self.bairro,
            phone=self.telefone,
            manager_name=self.nome_gestor,
            latitude=self.latitude,
            longitude=self.longitude,
            status=self.status,
        )


class UnidadeOut(BaseModel):
    """A unidade completa. `versao` é a mesma do cabeçalho `ETag` (006/R3.2)."""

    id: UUID
    nome: str
    cnes: str | None
    cnes_pendente: bool
    tipo_unidade_id: int
    distrito_id: int
    cep: str
    endereco: str
    bairro: str | None
    telefone: str | None
    nome_gestor: str | None
    horario_funcionamento: dict[str, Any] | None
    latitude: float | None
    longitude: float | None
    status: StatusDaUnidade
    pendencias: int
    versao: int
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def de(cls, unidade: Unidade) -> Self:
        return cls(
            id=unidade.id,
            nome=unidade.name,
            cnes=unidade.cnes,
            cnes_pendente=unidade.cnes_pendente,
            tipo_unidade_id=unidade.unit_type_id,
            distrito_id=unidade.district_id,
            cep=unidade.cep,
            endereco=unidade.address,
            bairro=unidade.neighborhood,
            telefone=unidade.phone,
            nome_gestor=unidade.manager_name,
            horario_funcionamento=(
                None if unidade.opening_hours is None else dict(unidade.opening_hours)
            ),
            latitude=None if unidade.latitude is None else float(unidade.latitude),
            longitude=None if unidade.longitude is None else float(unidade.longitude),
            status=cast(StatusDaUnidade, unidade.status),  # o CHECK do banco garante
            pendencias=unidade.pending_issues,
            versao=unidade.version,
            criado_em=unidade.created_at,
            atualizado_em=unidade.updated_at,
        )


_CAMPOS_DA_UNIDADE = {
    "nome": "name",
    "cnes": "cnes",
    "tipo_unidade_id": "unit_type_id",
    "distrito_id": "district_id",
    "cep": "cep",
    "endereco": "address",
    "bairro": "neighborhood",
    "telefone": "phone",
    "nome_gestor": "manager_name",
    "latitude": "latitude",
    "longitude": "longitude",
    "status": "status",
}


class UnidadeUpdate(BaseModel):
    """PATCH: todos opcionais; só os enviados mudam (006/R3.1). Nulo limpa um campo opcional; num
    obrigatório, o caso de uso responde 422."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str | None = Field(default=None, min_length=1, max_length=200)
    cnes: _Cnes | None = None
    tipo_unidade_id: _IdDeReferencia | None = None
    distrito_id: _IdDeReferencia | None = None
    cep: _Cep | None = None
    endereco: str | None = Field(default=None, min_length=1, max_length=200)
    bairro: str | None = Field(default=None, min_length=1, max_length=100)
    telefone: _Telefone | None = None
    nome_gestor: str | None = Field(default=None, min_length=1, max_length=150)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180, max_digits=9, decimal_places=6)
    status: StatusDaUnidade | None = None

    def alteracoes(self) -> dict[str, object]:
        """Campo do domínio → valor, só dos campos presentes no corpo."""
        return {_CAMPOS_DA_UNIDADE[campo]: getattr(self, campo) for campo in self.model_fields_set}


class DesativacaoIn(BaseModel):
    """006/R4.1: a desativação exige motivo."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    motivo: str = Field(min_length=3, max_length=500)


StatusDoEquipamento = Literal["ativo", "inativo", "em_manutencao"]
StatusDoServico = Literal["ativo", "inativo"]


class EquipamentoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    tipo_codigo: str = Field(min_length=1, max_length=50, description="Código do tipo.")
    quantidade: int = Field(default=1, ge=1, le=100_000)
    status: StatusDoEquipamento = "ativo"
    cnes: _Cnes | None = None

    def dados(self) -> DadosDoEquipamento:
        return DadosDoEquipamento(
            name=self.nome,
            equipment_type_code=self.tipo_codigo,
            quantity=self.quantidade,
            status=self.status,
            cnes=self.cnes,
        )


_CAMPOS_DO_EQUIPAMENTO = {
    "nome": "name",
    "tipo_codigo": "equipment_type_code",
    "quantidade": "quantity",
    "status": "status",
    "cnes": "cnes",
}


class EquipamentoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str | None = Field(default=None, min_length=1, max_length=200)
    tipo_codigo: str | None = Field(default=None, min_length=1, max_length=50)
    quantidade: int | None = Field(default=None, ge=1, le=100_000)
    status: StatusDoEquipamento | None = None
    cnes: _Cnes | None = None

    def alteracoes(self) -> dict[str, object]:
        return {
            _CAMPOS_DO_EQUIPAMENTO[campo]: getattr(self, campo) for campo in self.model_fields_set
        }


class EquipamentoOut(BaseModel):
    id: UUID
    unidade_id: UUID | None
    nome: str
    tipo_codigo: str
    quantidade: int
    status: str
    cnes: str | None
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def de(cls, equipamento: Equipamento) -> Self:
        return cls(
            id=equipamento.id,
            unidade_id=equipamento.unit_id,
            nome=equipamento.name,
            tipo_codigo=equipamento.equipment_type_code,
            quantidade=equipamento.quantity,
            status=equipamento.status,
            cnes=equipamento.cnes,
            criado_em=equipamento.created_at,
            atualizado_em=equipamento.updated_at,
        )


class ServicoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    tipo_servico_id: _IdDeReferencia
    no_cnes: bool = Field(default=False, description="Se o serviço consta no CNES (006/R6.3).")
    status: StatusDoServico = "ativo"
    equipamento_id: UUID | None = None

    def dados(self) -> DadosDoServico:
        return DadosDoServico(
            name=self.nome,
            service_type_id=self.tipo_servico_id,
            in_cnes=self.no_cnes,
            status=self.status,
            equipment_id=self.equipamento_id,
        )


_CAMPOS_DO_SERVICO = {
    "nome": "name",
    "tipo_servico_id": "service_type_id",
    "no_cnes": "in_cnes",
    "status": "status",
    "equipamento_id": "equipment_id",
}


class ServicoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nome: str | None = Field(default=None, min_length=1, max_length=200)
    tipo_servico_id: _IdDeReferencia | None = None
    no_cnes: bool | None = None
    status: StatusDoServico | None = None
    equipamento_id: UUID | None = None

    def alteracoes(self) -> dict[str, object]:
        return {_CAMPOS_DO_SERVICO[campo]: getattr(self, campo) for campo in self.model_fields_set}


class ServicoOut(BaseModel):
    id: UUID
    unidade_id: UUID | None
    equipamento_id: UUID | None
    tipo_servico_id: int
    nome: str
    no_cnes: bool
    status: str
    criado_em: datetime
    atualizado_em: datetime

    @classmethod
    def de(cls, servico: Servico) -> Self:
        return cls(
            id=servico.id,
            unidade_id=servico.unit_id,
            equipamento_id=servico.equipment_id,
            tipo_servico_id=servico.service_type_id,
            nome=servico.name,
            no_cnes=servico.in_cnes,
            status=servico.status,
            criado_em=servico.created_at,
            atualizado_em=servico.updated_at,
        )


class UnidadeDetalheOut(UnidadeOut):
    """006/R2.5: a unidade com os equipamentos e serviços vinculados."""

    equipamentos: list[EquipamentoOut]
    servicos: list[ServicoOut]

    @classmethod
    def do_detalhe(cls, detalhe: DetalheDaUnidade) -> Self:
        base = UnidadeOut.de(detalhe.unidade).model_dump()
        return cls(
            **base,
            equipamentos=[EquipamentoOut.de(e) for e in detalhe.equipamentos],
            servicos=[ServicoOut.de(s) for s in detalhe.servicos],
        )


_Codigo = Annotated[
    str, Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_\-]+$", description="Código.")
]


class ReferenciaCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    codigo: _Codigo
    nome: str = Field(min_length=1, max_length=100)
    area_tecnica_id: _IdDeReferencia | None = Field(
        default=None, description="Obrigatória só em tipos de unidade."
    )

    def dados(self) -> DadosDaReferencia:
        return DadosDaReferencia(
            code=self.codigo, name=self.nome, technical_area_id=self.area_tecnica_id
        )


_CAMPOS_DA_REFERENCIA = {
    "codigo": "code",
    "nome": "name",
    "ativo": "is_active",
    "area_tecnica_id": "technical_area_id",
}


class ReferenciaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    codigo: _Codigo | None = None
    nome: str | None = Field(default=None, min_length=1, max_length=100)
    ativo: bool | None = None
    area_tecnica_id: _IdDeReferencia | None = None

    def alteracoes(self) -> dict[str, object]:
        return {
            _CAMPOS_DA_REFERENCIA[campo]: getattr(self, campo)
            for campo in self.model_fields_set
            if getattr(self, campo) is not None
        }


class ReferenciaOut(BaseModel):
    id: int
    codigo: str
    nome: str
    ativo: bool
    area_tecnica_id: int | None

    @classmethod
    def de(cls, referencia: Referencia) -> Self:
        return cls(
            id=referencia.id,
            codigo=referencia.code,
            nome=referencia.name,
            ativo=referencia.is_active,
            area_tecnica_id=referencia.technical_area_id,
        )
