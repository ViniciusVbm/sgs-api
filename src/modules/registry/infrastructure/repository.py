"""Repositórios do cadastro sobre a sessão SQLAlchemy de quem os usa.

SQL escrito à mão, em `sql/*.sql`, executado com `text()` e parâmetros nomeados (ADR-0009). As
referências usam os modelos de `sql/modelos/`, em que `{tabela}` e `{area}` são trocados na carga
do módulo só pelos nomes fixos de `TipoDeReferencia`.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import RowMapping, TextClause, bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.escopo import parametros_de_escopo
from src.core.sql import consulta
from src.modules.registry.domain.ports import EscopoDeLeitura, UnicidadeViolada
from src.modules.registry.domain.referencias import DadosDaReferencia, Referencia, TipoDeReferencia
from src.modules.registry.domain.unidade import (
    CAMPOS_DE_NEGOCIO,
    DadosDaUnidade,
    FiltrosDeUnidade,
    Unidade,
)
from src.modules.registry.domain.vinculos import (
    CAMPOS_DO_EQUIPAMENTO,
    CAMPOS_DO_SERVICO,
    DadosDoEquipamento,
    DadosDoServico,
    Equipamento,
    Servico,
)

_SQL = Path(__file__).parent / "sql"

# O JSONB declarado faz o SQLAlchemy serializar o dicionário do horário de funcionamento.
_INSERIR_UNIDADE = consulta(_SQL / "insert_health_unit.sql").bindparams(
    bindparam("opening_hours", type_=JSONB)
)
_AREA_DO_TIPO = consulta(_SQL / "unit_type_technical_area.sql")
_DISTRITO_ATIVO = consulta(_SQL / "district_is_active.sql")
_ID_PELO_CNES = consulta(_SQL / "health_unit_id_by_cnes.sql")
_ID_PELO_NOME = consulta(_SQL / "health_unit_id_by_name.sql")
_LISTAR_UNIDADES = consulta(_SQL / "list_health_units.sql")
_UNIDADE = consulta(_SQL / "health_unit_by_id.sql")
_UNIDADE_TRAVADA = consulta(_SQL / "health_unit_by_id_for_update.sql")
_ATUALIZAR_UNIDADE = consulta(_SQL / "update_health_unit.sql")
_DESATIVAR_UNIDADE = consulta(_SQL / "call_sp_deactivate_unit.sql")

_EQUIPAMENTOS = consulta(_SQL / "equipments_of_unit.sql")
_EQUIPAMENTO = consulta(_SQL / "equipment_by_id.sql")
_INSERIR_EQUIPAMENTO = consulta(_SQL / "insert_equipment.sql")
_ATUALIZAR_EQUIPAMENTO = consulta(_SQL / "update_equipment.sql")
_SERVICOS_DO_EQUIPAMENTO = consulta(_SQL / "services_linked_to_equipment.sql")
_REMOVER_EQUIPAMENTO = consulta(_SQL / "delete_equipment.sql")
_TIPO_DE_EQUIPAMENTO_ATIVO = consulta(_SQL / "equipment_type_is_active.sql")
_SERVICOS = consulta(_SQL / "services_of_unit.sql")
_SERVICO = consulta(_SQL / "service_by_id.sql")
_INSERIR_SERVICO = consulta(_SQL / "insert_service.sql")
_ATUALIZAR_SERVICO = consulta(_SQL / "update_service.sql")
_REMOVER_SERVICO = consulta(_SQL / "delete_service.sql")
_TIPO_DE_SERVICO_ATIVO = consulta(_SQL / "service_type_is_active.sql")

_INSERIR_TIPO_DE_UNIDADE = consulta(_SQL / "insert_unit_type.sql")
_ATUALIZAR_AREA_DO_TIPO = consulta(_SQL / "update_unit_type_area.sql")
_AREA_EXISTE = consulta(_SQL / "technical_area_exists.sql")
_EQUIPAMENTOS_COM_CODIGO = consulta(_SQL / "equipments_with_type_code.sql")

# Colunas que o PATCH da unidade pode alterar (`update_health_unit.sql`).
_ATUALIZAVEIS_DA_UNIDADE = (
    "name",
    "cnes",
    "unit_type_id",
    "district_id",
    "cep",
    "address",
    "neighborhood",
    "phone",
    "manager_name",
    "latitude",
    "longitude",
    "status",
)


def _modelo(nome: str, tipo: TipoDeReferencia) -> TextClause:
    """O modelo `sql/modelos/<nome>` com a tabela do tipo. Só nomes do enum entram no texto."""
    area = "technical_area_id" if tipo.tem_area else "CAST(NULL AS smallint)"
    texto = (_SQL / "modelos" / nome).read_text(encoding="utf-8")
    return text(texto.replace("{tabela}", tipo.tabela).replace("{area}", area))


_REFERENCIAS: dict[str, dict[TipoDeReferencia, TextClause]] = {
    nome: {tipo: _modelo(f"{nome}.sql", tipo) for tipo in TipoDeReferencia}
    for nome in ("reference_list", "reference_by_id", "reference_insert", "reference_update")
}


def _com_marcas(campos: Mapping[str, object], atualizaveis: Sequence[str]) -> dict[str, object]:
    """Parâmetros do UPDATE de texto fixo: o valor e `set_<coluna>` de cada coluna alterável."""
    desconhecidos = set(campos) - set(atualizaveis)
    if desconhecidos:
        raise ValueError(f"campos não atualizáveis: {sorted(desconhecidos)}")
    parametros: dict[str, object] = {}
    for coluna in atualizaveis:
        parametros[f"set_{coluna}"] = coluna in campos
        parametros[coluna] = campos.get(coluna)
    return parametros


class SqlRepositorioDeUnidades:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def area_do_tipo(self, unit_type_id: int) -> int | None:
        area: int | None = await self._session.scalar(_AREA_DO_TIPO, {"unit_type_id": unit_type_id})
        return area

    async def distrito_ativo(self, district_id: int) -> bool:
        return bool(await self._session.scalar(_DISTRITO_ATIVO, {"district_id": district_id}))

    async def inserir(self, id_: UUID, dados: DadosDaUnidade) -> Unidade | None:
        parametros: dict[str, Any] = {campo: getattr(dados, campo) for campo in CAMPOS_DE_NEGOCIO}
        resultado = await self._session.execute(_INSERIR_UNIDADE, {"id": id_, **parametros})
        linha = resultado.mappings().one_or_none()
        return None if linha is None else _unidade(linha)

    async def com_cnes(self, cnes: str) -> UUID | None:
        unidade: UUID | None = await self._session.scalar(_ID_PELO_CNES, {"cnes": cnes})
        return unidade

    async def com_nome(self, district_id: int, name: str) -> UUID | None:
        unidade: UUID | None = await self._session.scalar(
            _ID_PELO_NOME, {"district_id": district_id, "name": name}
        )
        return unidade

    async def listar(
        self, escopo: EscopoDeLeitura, filtros: FiltrosDeUnidade, limite: int, deslocamento: int
    ) -> tuple[list[Unidade], int]:
        parametros = {
            **parametros_de_escopo(escopo),
            "q": filtros.q,
            "unit_type_id": filtros.tipo,
            "technical_area_id": filtros.area,
            "district_id": filtros.distrito,
            "status": filtros.status,
            "com_pendencias": filtros.com_pendencias,
            "ordem": filtros.ordem,
            "limit": limite,
            "offset": deslocamento,
        }
        linhas = list((await self._session.execute(_LISTAR_UNIDADES, parametros)).mappings())
        if linhas:
            total = int(linhas[0]["total"])
        elif deslocamento == 0:
            total = 0
        else:
            primeira = await self._session.execute(
                _LISTAR_UNIDADES, {**parametros, "limit": 1, "offset": 0}
            )
            linha = primeira.mappings().first()
            total = 0 if linha is None else int(linha["total"])
        return [_unidade(linha) for linha in linhas], total

    async def obter(self, id_: UUID, *, travar: bool = False) -> Unidade | None:
        resultado = await self._session.execute(
            _UNIDADE_TRAVADA if travar else _UNIDADE, {"id": id_}
        )
        linha = resultado.mappings().one_or_none()
        return None if linha is None else _unidade(linha)

    async def atualizar(
        self, id_: UUID, campos: Mapping[str, object], versao: int
    ) -> Unidade | None:
        parametros = {
            "id": id_,
            "version": versao,
            **_com_marcas(campos, _ATUALIZAVEIS_DA_UNIDADE),
        }
        try:
            async with self._session.begin_nested():
                resultado = await self._session.execute(_ATUALIZAR_UNIDADE, parametros)
                linha = resultado.mappings().one_or_none()
        except IntegrityError as erro:
            raise UnicidadeViolada from erro
        return None if linha is None else _unidade(linha)

    async def desativar(self, id_: UUID) -> tuple[str, int] | None:
        try:
            async with self._session.begin_nested():
                resultado = await self._session.execute(_DESATIVAR_UNIDADE, {"id": id_})
                linha = resultado.one()
        except Exception as erro:
            if _sqlstate(erro) == "SGS01":
                return None
            raise
        return str(linha[0]), int(linha[1])


class SqlRepositorioDeVinculos:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def tipo_de_equipamento_ativo(self, codigo: str) -> bool:
        return bool(await self._session.scalar(_TIPO_DE_EQUIPAMENTO_ATIVO, {"code": codigo}))

    async def tipo_de_servico_ativo(self, id_: int) -> bool:
        return bool(await self._session.scalar(_TIPO_DE_SERVICO_ATIVO, {"id": id_}))

    async def equipamentos(self, unit_id: UUID | None) -> list[Equipamento]:
        resultado = await self._session.execute(_EQUIPAMENTOS, {"unit_id": unit_id})
        return [Equipamento(**linha) for linha in resultado.mappings()]

    async def obter_equipamento(self, id_: UUID) -> Equipamento | None:
        linha = (await self._session.execute(_EQUIPAMENTO, {"id": id_})).mappings().one_or_none()
        return None if linha is None else Equipamento(**linha)

    async def inserir_equipamento(
        self, id_: UUID, unit_id: UUID | None, dados: DadosDoEquipamento
    ) -> Equipamento:
        parametros = {campo: getattr(dados, campo) for campo in CAMPOS_DO_EQUIPAMENTO}
        resultado = await self._session.execute(
            _INSERIR_EQUIPAMENTO, {"id": id_, "unit_id": unit_id, **parametros}
        )
        return Equipamento(**resultado.mappings().one())

    async def atualizar_equipamento(
        self, id_: UUID, campos: Mapping[str, object]
    ) -> Equipamento | None:
        resultado = await self._session.execute(
            _ATUALIZAR_EQUIPAMENTO, {"id": id_, **_com_marcas(campos, CAMPOS_DO_EQUIPAMENTO)}
        )
        linha = resultado.mappings().one_or_none()
        return None if linha is None else Equipamento(**linha)

    async def remover_equipamento(self, id_: UUID) -> int:
        desligados = int(await self._session.scalar(_SERVICOS_DO_EQUIPAMENTO, {"id": id_}) or 0)
        await self._session.execute(_REMOVER_EQUIPAMENTO, {"id": id_})
        return desligados

    async def servicos(self, unit_id: UUID | None) -> list[Servico]:
        resultado = await self._session.execute(_SERVICOS, {"unit_id": unit_id})
        return [Servico(**linha) for linha in resultado.mappings()]

    async def obter_servico(self, id_: UUID) -> Servico | None:
        linha = (await self._session.execute(_SERVICO, {"id": id_})).mappings().one_or_none()
        return None if linha is None else Servico(**linha)

    async def inserir_servico(
        self, id_: UUID, unit_id: UUID | None, dados: DadosDoServico
    ) -> Servico:
        parametros = {campo: getattr(dados, campo) for campo in CAMPOS_DO_SERVICO}
        resultado = await self._session.execute(
            _INSERIR_SERVICO, {"id": id_, "unit_id": unit_id, **parametros}
        )
        return Servico(**resultado.mappings().one())

    async def atualizar_servico(self, id_: UUID, campos: Mapping[str, object]) -> Servico | None:
        resultado = await self._session.execute(
            _ATUALIZAR_SERVICO, {"id": id_, **_com_marcas(campos, CAMPOS_DO_SERVICO)}
        )
        linha = resultado.mappings().one_or_none()
        return None if linha is None else Servico(**linha)

    async def remover_servico(self, id_: UUID) -> bool:
        resultado = await self._session.execute(_REMOVER_SERVICO, {"id": id_})
        return bool(getattr(resultado, "rowcount", 0))


class SqlRepositorioDeReferencias:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def listar(self, tipo: TipoDeReferencia) -> list[Referencia]:
        resultado = await self._session.execute(_REFERENCIAS["reference_list"][tipo])
        return [Referencia(**linha) for linha in resultado.mappings()]

    async def obter(self, tipo: TipoDeReferencia, id_: int) -> Referencia | None:
        resultado = await self._session.execute(_REFERENCIAS["reference_by_id"][tipo], {"id": id_})
        linha = resultado.mappings().one_or_none()
        return None if linha is None else Referencia(**linha)

    async def area_existe(self, id_: int) -> bool:
        return bool(await self._session.scalar(_AREA_EXISTE, {"id": id_}))

    async def inserir(self, tipo: TipoDeReferencia, dados: DadosDaReferencia) -> Referencia:
        if tipo.tem_area:
            consulta_ = _INSERIR_TIPO_DE_UNIDADE
            parametros: dict[str, object] = {
                "code": dados.code,
                "name": dados.name,
                "technical_area_id": dados.technical_area_id,
            }
        else:
            consulta_ = _REFERENCIAS["reference_insert"][tipo]
            parametros = {"code": dados.code, "name": dados.name}
        linha = (await self._session.execute(consulta_, parametros)).mappings().one_or_none()
        if linha is None:
            raise UnicidadeViolada
        return Referencia(**linha)

    async def atualizar(
        self, tipo: TipoDeReferencia, id_: int, campos: Mapping[str, object]
    ) -> Referencia:
        area = campos.get("technical_area_id")
        basicos = {c: v for c, v in campos.items() if c != "technical_area_id"}
        try:
            async with self._session.begin_nested():
                if tipo.tem_area and "technical_area_id" in campos:
                    await self._session.execute(
                        _ATUALIZAR_AREA_DO_TIPO, {"id": id_, "technical_area_id": area}
                    )
                resultado = await self._session.execute(
                    _REFERENCIAS["reference_update"][tipo],
                    {"id": id_, **_com_marcas(basicos, ("code", "name", "is_active"))},
                )
                linha = resultado.mappings().one()
        except IntegrityError as erro:
            raise UnicidadeViolada from erro
        return Referencia(**linha)

    async def equipamentos_com_codigo(self, codigo: str) -> int:
        return int(await self._session.scalar(_EQUIPAMENTOS_COM_CODIGO, {"code": codigo}) or 0)


def _unidade(linha: RowMapping) -> Unidade:
    return Unidade(**{chave: valor for chave, valor in linha.items() if chave != "total"})


def _sqlstate(erro: BaseException) -> str | None:
    """SQLSTATE do erro do driver, se houver (o asyncpg o expõe em `sqlstate`)."""
    original = getattr(erro, "orig", None)
    return getattr(original, "sqlstate", None) or getattr(
        getattr(original, "__cause__", None), "sqlstate", None
    )
