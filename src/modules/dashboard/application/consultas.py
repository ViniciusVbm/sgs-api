"""Casos de uso das consultas de qualidade do cadastro (spec 011, R2; design § Fluxo, Consulta).

Cada consulta obtém o escopo de leitura do usuário para `dashboard:read` (spec 003) e chama a
porta `ConsultasDashboard`, que executa o SQL com o escopo como parâmetros.
"""

from src.core.errors import DomainValidationError, FieldError
from src.modules.access.application.autorizacao import UsuarioAtual, escopo_de_leitura
from src.modules.access.domain.authorization import pode
from src.modules.dashboard.domain.catalogo import CATALOGO, POR_NOME, EntradaDoCatalogo
from src.modules.dashboard.domain.consultas import (
    Filtros,
    ItemConciliacao,
    Linha,
    Pagina,
    Resultado,
    Resumo,
    SituacaoConciliacao,
    UnidadeResumo,
)
from src.modules.dashboard.domain.ports import ConsultasDashboard

# Reexportados para a camada api, que só importa a application.
__all__ = [
    "CATALOGO",
    "PERMISSAO",
    "ConsultasDashboard",
    "EntradaDoCatalogo",
    "Filtros",
    "ItemConciliacao",
    "Linha",
    "Pagina",
    "Resultado",
    "Resumo",
    "SituacaoConciliacao",
    "UnidadeResumo",
    "catalogo",
    "conciliacao_unidade_equipamento",
    "consultar",
    "resumo",
    "unidades_sem_servico",
]

PERMISSAO = "dashboard:read"


async def unidades_sem_servico(
    consultas: ConsultasDashboard, usuario: UsuarioAtual, filtros: Filtros, pagina: Pagina
) -> Resultado[UnidadeResumo]:
    """011/R2.1, R2.5: unidades não inativas sem serviço, no escopo de leitura do usuário."""
    await _conferir_filtros(consultas, filtros)
    escopo = escopo_de_leitura(usuario, PERMISSAO)
    return await consultas.unidades_sem_servico(escopo, filtros, pagina)


async def conciliacao_unidade_equipamento(
    consultas: ConsultasDashboard, usuario: UsuarioAtual, filtros: Filtros, pagina: Pagina
) -> Resultado[ItemConciliacao]:
    """011/R2.2, R2.5, R2.6: conciliação unidade x equipamento no escopo de leitura do usuário;
    equipamento sem unidade só com escopo global."""
    await _conferir_filtros(consultas, filtros)
    escopo = escopo_de_leitura(usuario, PERMISSAO)
    return await consultas.conciliacao_unidade_equipamento(escopo, filtros, pagina)


async def _conferir_filtros(consultas: ConsultasDashboard, filtros: Filtros) -> None:
    """011/R2.9: distrito ou tipo inexistente dá 422 antes de a consulta rodar. O formato (número
    inteiro no intervalo do id) já foi conferido pelo schema da rota."""
    erros = []
    if filtros.distrito is not None and not await consultas.distrito_existe(filtros.distrito):
        erros.append(FieldError(campo="distrito", mensagem="Distrito inexistente."))
    if filtros.tipo is not None and not await consultas.tipo_de_unidade_existe(filtros.tipo):
        erros.append(FieldError(campo="tipo", mensagem="Tipo de unidade inexistente."))
    if filtros.area is not None and not await consultas.area_existe(filtros.area):
        erros.append(FieldError(campo="area", mensagem="Área técnica inexistente."))
    if erros:
        raise DomainValidationError("O filtro aponta para uma referência que não existe.", erros)


async def consultar(
    nome: str,
    consultas: ConsultasDashboard,
    usuario: UsuarioAtual,
    filtros: Filtros,
    pagina: Pagina | None = None,
    extras: dict[str, object] | None = None,
) -> Resultado[Linha]:
    """Executa uma consulta do catálogo (011/T12, T13; 009/R2) no escopo de leitura do usuário.

    As paginadas devolvem a página e o total; as agregadas, todas as linhas (total = linhas).
    """
    entrada = POR_NOME[nome]
    if entrada.arquivo_sql is None:
        raise ValueError(f"a consulta {nome!r} tem rota própria")
    await _conferir_filtros(consultas, filtros)
    escopo = escopo_de_leitura(usuario, entrada.permissao)
    if entrada.paginada:
        if pagina is None:
            raise ValueError(f"a consulta {nome!r} é paginada")
        return await consultas.pagina(entrada.arquivo_sql, escopo, filtros, pagina, extras)
    linhas = await consultas.linhas(entrada.arquivo_sql, escopo, filtros, extras)
    return Resultado(itens=linhas, total=len(linhas))


async def resumo(consultas: ConsultasDashboard, usuario: UsuarioAtual, filtros: Filtros) -> Resumo:
    """009/R1: unidades por categoria, qualidade e alterações, no escopo do usuário (R1.5)."""
    await _conferir_filtros(consultas, filtros)
    escopo = escopo_de_leitura(usuario, PERMISSAO)
    categorias = await consultas.linhas("units_by_category.sql", escopo, filtros)
    (qualidade,) = await consultas.linhas("summary_quality.sql", escopo, filtros)
    (alteracoes,) = await consultas.linhas("summary_changes.sql", escopo, filtros)
    recentes = await consultas.linhas("recent_changes.sql", escopo, filtros, {"limit": 10})
    return Resumo(
        categorias=categorias, qualidade=qualidade, alteracoes=alteracoes, recentes=recentes
    )


def catalogo(usuario: UsuarioAtual) -> list[EntradaDoCatalogo]:
    """011/R3.2: só as consultas que o usuário tem permissão de executar."""
    return [entrada for entrada in CATALOGO if pode(usuario.permissoes, entrada.permissao)]
