"""Consultas do dashboard em SQL escrito à mão (ADR-0009; design da 011 § Consultas).

Cada consulta está em `sql/<nome>.sql`, com o cabeçalho que a explica, e é lida uma vez, na carga
do módulo. O escopo de leitura entra pelos parâmetros `:scope_*` do fragmento fixo
(`src.core.escopo.parametros_de_escopo`) e os filtros, pelos seus parâmetros: nenhum valor é
interpolado no texto.
"""

from pathlib import Path
from typing import Any

from sqlalchemy import TextClause, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.escopo import parametros_de_escopo
from src.modules.dashboard.domain.consultas import (
    Filtros,
    ItemConciliacao,
    Pagina,
    Resultado,
    SituacaoConciliacao,
    UnidadeResumo,
)
from src.modules.dashboard.domain.ports import EscopoDeLeitura

_PASTA_SQL = Path(__file__).resolve().parent / "sql"


def _consulta(nome: str) -> TextClause:
    return text((_PASTA_SQL / f"{nome}.sql").read_text(encoding="utf-8"))


_UNIDADES_SEM_SERVICO = _consulta("units_without_services")
_CONCILIACAO_UNIDADE_EQUIPAMENTO = _consulta("unit_equipment_reconciliation")

# Conferência dos filtros contra as referências da 006 (011/R2.9). Não são consultas da
# disciplina: só dizem se o id existe, antes de a consulta de verdade rodar.
_DISTRITO_EXISTE = text("SELECT EXISTS (SELECT 1 FROM districts WHERE id = :id)")
_TIPO_DE_UNIDADE_EXISTE = text("SELECT EXISTS (SELECT 1 FROM unit_types WHERE id = :id)")


class SqlConsultasDashboard:
    """`ConsultasDashboard` sobre a sessão SQLAlchemy de quem a usa."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def distrito_existe(self, distrito: int) -> bool:
        return bool(await self._session.scalar(_DISTRITO_EXISTE, {"id": distrito}))

    async def tipo_de_unidade_existe(self, tipo: int) -> bool:
        return bool(await self._session.scalar(_TIPO_DE_UNIDADE_EXISTE, {"id": tipo}))

    async def unidades_sem_servico(
        self, escopo: EscopoDeLeitura, filtros: Filtros, pagina: Pagina
    ) -> Resultado[UnidadeResumo]:
        linhas, total = await self._pagina(_UNIDADES_SEM_SERVICO, escopo, filtros, pagina)
        return Resultado(
            itens=tuple(
                UnidadeResumo(
                    id=linha["unit_id"],
                    nome=linha["name"],
                    cnes=linha["cnes"],
                    tipo=linha["unit_type_name"],
                    distrito=linha["district_name"],
                )
                for linha in linhas
            ),
            total=total,
        )

    async def conciliacao_unidade_equipamento(
        self, escopo: EscopoDeLeitura, filtros: Filtros, pagina: Pagina
    ) -> Resultado[ItemConciliacao]:
        linhas, total = await self._pagina(
            _CONCILIACAO_UNIDADE_EQUIPAMENTO, escopo, filtros, pagina
        )
        return Resultado(
            itens=tuple(
                ItemConciliacao(
                    unidade_id=linha["unit_id"],
                    unidade_nome=linha["unit_name"],
                    distrito=linha["district_name"],
                    equipamento_id=linha["equipment_id"],
                    equipamento_nome=linha["equipment_name"],
                    equipamento_tipo=linha["equipment_type_name"],
                    situacao=SituacaoConciliacao(linha["situation"]),
                )
                for linha in linhas
            ),
            total=total,
        )

    async def _pagina(
        self, consulta: TextClause, escopo: EscopoDeLeitura, filtros: Filtros, pagina: Pagina
    ) -> tuple[list[dict[str, Any]], int]:
        """Linhas da página e total da consulta, que vem em cada linha (`count(*) OVER ()`).

        Numa página depois da última não volta linha nenhuma, e o total sai da primeira página.
        """
        parametros = {
            **parametros_de_escopo(escopo),
            "district_id": filtros.distrito,
            "unit_type_id": filtros.tipo,
            "limit": pagina.tamanho,
            "offset": pagina.offset,
        }
        linhas = [
            dict(linha) for linha in (await self._session.execute(consulta, parametros)).mappings()
        ]
        if linhas:
            return linhas, int(linhas[0]["total"])
        if pagina.offset == 0:
            return [], 0
        primeira = await self._session.execute(consulta, {**parametros, "limit": 1, "offset": 0})
        linha = primeira.mappings().first()
        return [], 0 if linha is None else int(linha["total"])
