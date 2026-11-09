"""Portas do módulo de cadastro.

Os repositórios trabalham sobre a transação de quem os usa (a da requisição, aberta pela
dependência `SessaoDeNegocio` da camada api): quem chama abre, confirma ou desfaz.
"""

from collections.abc import Mapping, Sequence
from typing import Protocol
from uuid import UUID

from src.modules.registry.domain.referencias import DadosDaReferencia, Referencia, TipoDeReferencia
from src.modules.registry.domain.unidade import DadosDaUnidade, FiltrosDeUnidade, Unidade
from src.modules.registry.domain.vinculos import (
    DadosDoEquipamento,
    DadosDoServico,
    Equipamento,
    Servico,
)


class EscopoDeLeitura(Protocol):
    """O que a listagem lê do escopo de leitura do usuário (`EscopoLeitura` da spec 003)."""

    @property
    def global_(self) -> bool: ...

    @property
    def areas(self) -> Sequence[int]: ...

    @property
    def distritos(self) -> Sequence[int]: ...

    @property
    def unidades(self) -> Sequence[UUID]: ...


class RepositorioDeUnidades(Protocol):
    async def area_do_tipo(self, unit_type_id: int) -> int | None:
        """Área técnica do tipo de unidade; `None` se o tipo não existe ou está desativado."""
        ...

    async def distrito_ativo(self, district_id: int) -> bool:
        """Se o distrito sanitário existe e está ativo."""
        ...

    async def inserir(self, id_: UUID, dados: DadosDaUnidade) -> Unidade | None:
        """Grava a unidade nova e a devolve como ficou no banco; `None`, sem gravar nada, se ela
        repete o CNES ou o nome normalizado no distrito de outra (006/R1.3, R1.4)."""
        ...

    async def com_cnes(self, cnes: str) -> UUID | None:
        """Id da unidade com esse CNES, se houver."""
        ...

    async def com_nome(self, district_id: int, name: str) -> UUID | None:
        """Id da unidade do distrito com o mesmo nome normalizado (`fn_normalize_name`), se
        houver."""
        ...

    async def listar(
        self, escopo: EscopoDeLeitura, filtros: FiltrosDeUnidade, limite: int, deslocamento: int
    ) -> tuple[list[Unidade], int]:
        """Uma página das unidades no escopo e nos filtros, e o total (006/R2.1 a R2.4, R2.6)."""
        ...

    async def obter(self, id_: UUID, *, travar: bool = False) -> Unidade | None:
        """A unidade, ou `None`. `travar` lê com `FOR UPDATE`, para a atualização."""
        ...

    async def atualizar(
        self, id_: UUID, campos: Mapping[str, object], versao: int
    ) -> Unidade | None:
        """Grava os campos se a versão ainda for `versao`; `None` se a versão mudou (412).

        Quem incrementa a versão é o trigger da 011 (R8); o repositório não. Levanta
        `UnicidadeViolada` se a alteração repete o CNES ou o nome no distrito de outra.
        """
        ...

    async def desativar(self, id_: UUID) -> tuple[str, int] | None:
        """Chama `sp_deactivate_unit` (011/R6): status anterior e versão; `None` se não existe."""
        ...


class UnicidadeViolada(Exception):  # noqa: N818 (é um sinal entre camadas, não um erro de API)
    """O banco recusou a escrita por repetir uma chave única (CNES, nome, código)."""


class RepositorioDeVinculos(Protocol):
    """Equipamentos e serviços (006/R5, R6)."""

    async def tipo_de_equipamento_ativo(self, codigo: str) -> bool: ...

    async def tipo_de_servico_ativo(self, id_: int) -> bool: ...

    async def equipamentos(self, unit_id: UUID | None) -> list[Equipamento]:
        """Os equipamentos da unidade; com `None`, os sem unidade."""
        ...

    async def obter_equipamento(self, id_: UUID) -> Equipamento | None: ...

    async def inserir_equipamento(
        self, id_: UUID, unit_id: UUID | None, dados: DadosDoEquipamento
    ) -> Equipamento: ...

    async def atualizar_equipamento(
        self, id_: UUID, campos: Mapping[str, object]
    ) -> Equipamento | None: ...

    async def remover_equipamento(self, id_: UUID) -> int:
        """Apaga o equipamento e devolve quantos serviços ficaram sem ele (ON DELETE SET NULL,
        011/R9.1)."""
        ...

    async def servicos(self, unit_id: UUID | None) -> list[Servico]:
        """Os serviços da unidade; com `None`, os soltos."""
        ...

    async def obter_servico(self, id_: UUID) -> Servico | None: ...

    async def inserir_servico(
        self, id_: UUID, unit_id: UUID | None, dados: DadosDoServico
    ) -> Servico: ...

    async def atualizar_servico(
        self, id_: UUID, campos: Mapping[str, object]
    ) -> Servico | None: ...

    async def remover_servico(self, id_: UUID) -> bool: ...


class RepositorioDeReferencias(Protocol):
    """Tabelas de referência (006/R7)."""

    async def listar(self, tipo: TipoDeReferencia) -> list[Referencia]: ...

    async def obter(self, tipo: TipoDeReferencia, id_: int) -> Referencia | None: ...

    async def area_existe(self, id_: int) -> bool: ...

    async def inserir(self, tipo: TipoDeReferencia, dados: DadosDaReferencia) -> Referencia:
        """Levanta `UnicidadeViolada` se o código já existe."""
        ...

    async def atualizar(
        self, tipo: TipoDeReferencia, id_: int, campos: Mapping[str, object]
    ) -> Referencia:
        """Levanta `UnicidadeViolada` se o código novo já existe."""
        ...

    async def equipamentos_com_codigo(self, codigo: str) -> int:
        """Quantos equipamentos usam o código de tipo (para `equipamentos_afetados`, 006/R7.3)."""
        ...
