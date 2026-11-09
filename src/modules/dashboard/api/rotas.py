"""Rotas das consultas de qualidade do cadastro (spec 011, R2; design § Rotas).

Todas são `GET` de leitura com `require("dashboard:read")` (011/R2.8), e cada consulta aplica o
escopo de leitura do usuário (011/R2.5). A sessão é só de leitura: nada é gravado.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request

from src.core.fuso import agora_em_recife
from src.core.paginacao import TAMANHO_PADRAO, NumeroDaPagina, PaginaOut, TamanhoDaPagina
from src.core.problem import PROBLEM_JSON
from src.modules.access.api.deps import UsuarioAtual, require
from src.modules.dashboard.api.schemas import (
    AlteracaoRecenteOut,
    AlteracoesPorPeriodoOut,
    AlteracoesResumoOut,
    CategoriaOut,
    ConciliacaoOut,
    DistritoSemCnesOut,
    EntradaDoCatalogoOut,
    EquipamentosPorTipoOut,
    InventarioOut,
    ItemDistribuicaoOut,
    QualidadeOut,
    ResumoOut,
    UnidadeForaDoCnesOut,
    UnidadeResumoOut,
    UnidadesResumoOut,
)
from src.modules.dashboard.application import consultas
from src.modules.dashboard.application.consultas import ConsultasDashboard, Filtros, Pagina

_ERROS: dict[int | str, dict[str, Any]] = {
    401: {"description": "Sem access token válido", "content": {PROBLEM_JSON: {}}},
    403: {"description": "Sem `dashboard:read`", "content": {PROBLEM_JSON: {}}},
    422: {
        "description": "Filtro mal formado, ou distrito ou tipo inexistente",
        "content": {PROBLEM_JSON: {}},
    },
}

router = APIRouter(prefix="/api/v1/dashboard/consultas", tags=["dashboard"], responses=_ERROS)

Leitor = Annotated[UsuarioAtual, Depends(require(consultas.PERMISSAO))]

# Ids de referência são `smallint` no banco: o limite barra no 422 o que não caberia (011/R2.9).
_ID_DE_REFERENCIA_MAXIMO = 32767


@dataclass(frozen=True, slots=True)
class _Pedido:
    filtros: Filtros
    pagina: Pagina


def _pedido(
    distrito: Annotated[
        int | None,
        Query(ge=1, le=_ID_DE_REFERENCIA_MAXIMO, description="Id do distrito sanitário."),
    ] = None,
    tipo: Annotated[
        int | None,
        Query(ge=1, le=_ID_DE_REFERENCIA_MAXIMO, description="Id do tipo de unidade."),
    ] = None,
    pagina: NumeroDaPagina = 1,
    tamanho: TamanhoDaPagina = TAMANHO_PADRAO,
) -> _Pedido:
    """Filtros de distrito e de tipo de unidade (011/R2.7) e a página pedida."""
    return _Pedido(Filtros(distrito=distrito, tipo=tipo), Pagina(numero=pagina, tamanho=tamanho))


Pedido = Annotated[_Pedido, Depends(_pedido)]


@router.get(
    "/unidades-sem-servico",
    summary="Unidades sem nenhum serviço cadastrado (anti join)",
)
async def unidades_sem_servico(
    request: Request, usuario: Leitor, pedido: Pedido
) -> PaginaOut[UnidadeResumoOut]:
    """011/R2.1: unidades não inativas sem serviço, no escopo de leitura do usuário."""
    async with request.app.state.sessoes() as sessao:
        porta: ConsultasDashboard = request.app.state.consultas_dashboard(sessao)
        resultado = await consultas.unidades_sem_servico(
            porta, usuario, pedido.filtros, pedido.pagina
        )
    return PaginaOut(
        itens=[UnidadeResumoOut.model_validate(item) for item in resultado.itens],
        total=resultado.total,
        pagina=pedido.pagina.numero,
        tamanho=pedido.pagina.tamanho,
    )


@router.get(
    "/conciliacao-unidade-equipamento",
    summary="Conciliação unidade x equipamento (full outer join)",
)
async def conciliacao_unidade_equipamento(
    request: Request, usuario: Leitor, pedido: Pedido
) -> PaginaOut[ConciliacaoOut]:
    """011/R2.2, R2.6: pares, unidades sem equipamento e, só com escopo global e sem filtro,
    equipamentos sem unidade."""
    async with request.app.state.sessoes() as sessao:
        porta: ConsultasDashboard = request.app.state.consultas_dashboard(sessao)
        resultado = await consultas.conciliacao_unidade_equipamento(
            porta, usuario, pedido.filtros, pedido.pagina
        )
    return PaginaOut(
        itens=[ConciliacaoOut.model_validate(item) for item in resultado.itens],
        total=resultado.total,
        pagina=pedido.pagina.numero,
        tamanho=pedido.pagina.tamanho,
    )


# ------------------------------------------------- consultas novas do catálogo


def _filtros(
    distrito: Annotated[
        int | None, Query(ge=1, le=_ID_DE_REFERENCIA_MAXIMO, description="Id do distrito.")
    ] = None,
    tipo: Annotated[
        int | None, Query(ge=1, le=_ID_DE_REFERENCIA_MAXIMO, description="Id do tipo de unidade.")
    ] = None,
    area: Annotated[
        int | None, Query(ge=1, le=_ID_DE_REFERENCIA_MAXIMO, description="Id da área técnica.")
    ] = None,
) -> Filtros:
    """Filtros de distrito, tipo de unidade e área técnica (011/R2.7; 009/R1.6)."""
    return Filtros(distrito=distrito, tipo=tipo, area=area)


FiltrosDoPainel = Annotated[Filtros, Depends(_filtros)]


async def _executar(
    request: Request,
    nome: str,
    usuario: UsuarioAtual,
    filtros: Filtros,
    pagina: Pagina | None = None,
    extras: dict[str, object] | None = None,
) -> consultas.Resultado[consultas.Linha]:
    async with request.app.state.sessoes() as sessao:
        porta: ConsultasDashboard = request.app.state.consultas_dashboard(sessao)
        return await consultas.consultar(nome, porta, usuario, filtros, pagina, extras)


@router.get(
    "/distritos-sem-cnes-acima-da-rede",
    summary="Distritos com percentual de unidades sem CNES acima da rede (subconsulta)",
)
async def distritos_sem_cnes_acima_da_rede(
    request: Request,
    usuario: Leitor,
    filtros: FiltrosDoPainel,
    pagina: NumeroDaPagina = 1,
    tamanho: TamanhoDaPagina = TAMANHO_PADRAO,
) -> PaginaOut[DistritoSemCnesOut]:
    """011/R2.3, R2.5: a "rede" é o escopo de leitura do usuário."""
    resultado = await _executar(
        request, "distritos-sem-cnes-acima-da-rede", usuario, filtros, Pagina(pagina, tamanho)
    )
    return PaginaOut(
        itens=[DistritoSemCnesOut.model_validate(linha) for linha in resultado.itens],
        total=resultado.total,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.get(
    "/unidades-com-servico-fora-do-cnes",
    summary="Unidades com ao menos um serviço fora do CNES (subconsulta EXISTS)",
)
async def unidades_com_servico_fora_do_cnes(
    request: Request,
    usuario: Leitor,
    filtros: FiltrosDoPainel,
    pagina: NumeroDaPagina = 1,
    tamanho: TamanhoDaPagina = TAMANHO_PADRAO,
) -> PaginaOut[UnidadeForaDoCnesOut]:
    """011/R2.4, R2.5."""
    resultado = await _executar(
        request, "unidades-com-servico-fora-do-cnes", usuario, filtros, Pagina(pagina, tamanho)
    )
    return PaginaOut(
        itens=[UnidadeForaDoCnesOut.model_validate(linha) for linha in resultado.itens],
        total=resultado.total,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.get("/unidades-por-categoria", summary="Unidades por status, tipo, área e distrito")
async def unidades_por_categoria(
    request: Request, usuario: Leitor, filtros: FiltrosDoPainel
) -> list[CategoriaOut]:
    """009/R2.1 (consulta da Etapa 03 reescrita)."""
    resultado = await _executar(request, "unidades-por-categoria", usuario, filtros)
    return [CategoriaOut.model_validate(linha) for linha in resultado.itens]


@router.get("/equipamentos-por-tipo-e-distrito", summary="Equipamentos por tipo e distrito")
async def equipamentos_por_tipo_e_distrito(
    request: Request, usuario: Leitor, filtros: FiltrosDoPainel
) -> list[EquipamentosPorTipoOut]:
    """009/R2.2 (consulta da Etapa 03 reescrita)."""
    resultado = await _executar(request, "equipamentos-por-tipo-e-distrito", usuario, filtros)
    return [EquipamentosPorTipoOut.model_validate(linha) for linha in resultado.itens]


@router.get("/alteracoes-por-periodo", summary="Alterações em 7 e 30 dias por distrito")
async def alteracoes_por_periodo(
    request: Request, usuario: Leitor, filtros: FiltrosDoPainel
) -> list[AlteracoesPorPeriodoOut]:
    """009/R2.3 (consulta da Etapa 03 reescrita sobre a `vw_unit_history`)."""
    resultado = await _executar(request, "alteracoes-por-periodo", usuario, filtros)
    return [AlteracoesPorPeriodoOut.model_validate(linha) for linha in resultado.itens]


@router.get("/alteracoes-recentes", summary="As 10 alterações mais recentes")
async def alteracoes_recentes(
    request: Request, usuario: Leitor, filtros: FiltrosDoPainel
) -> list[AlteracaoRecenteOut]:
    """009/R2.4 (consulta da Etapa 03 reescrita sobre a `vw_unit_history`)."""
    resultado = await _executar(
        request, "alteracoes-recentes", usuario, filtros, None, {"limit": 10}
    )
    return [AlteracaoRecenteOut.model_validate(linha) for linha in resultado.itens]


painel = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"], responses=_ERROS)

_SITUACOES = Literal["inativa", "com_pendencias", "sem_cnes", "regular"]


@painel.get("/consultas", summary="Catálogo das consultas e views disponíveis")
async def listar_catalogo(usuario: Leitor) -> list[EntradaDoCatalogoOut]:
    """011/R3: título, justificativa, parâmetros, colunas, permissão e gráfico sugerido de cada
    consulta, só das que o usuário pode executar (R3.2)."""
    return [EntradaDoCatalogoOut.model_validate(e) for e in consultas.catalogo(usuario)]


@painel.get("/inventario", summary="Inventário da rede (vw_unit_inventory)")
async def inventario(
    request: Request,
    usuario: Leitor,
    filtros: FiltrosDoPainel,
    situacao: _SITUACOES | None = None,
    pagina: NumeroDaPagina = 1,
    tamanho: TamanhoDaPagina = TAMANHO_PADRAO,
) -> PaginaOut[InventarioOut]:
    """011/R4.3: a partir da view, no escopo e nos filtros; `situacao` é a da
    `fn_registration_status`."""
    resultado = await _executar(
        request,
        "inventario",
        usuario,
        filtros,
        Pagina(pagina, tamanho),
        {"registration_status": situacao},
    )
    return PaginaOut(
        itens=[InventarioOut.model_validate(linha) for linha in resultado.itens],
        total=resultado.total,
        pagina=pagina,
        tamanho=tamanho,
    )


@painel.get("/resumo", summary="Resumo da rede: unidades, qualidade e alterações")
async def resumo(request: Request, usuario: Leitor, filtros: FiltrosDoPainel) -> ResumoOut:
    """009/R1.1 a R1.6, no escopo de leitura do usuário."""
    async with request.app.state.sessoes() as sessao:
        porta: ConsultasDashboard = request.app.state.consultas_dashboard(sessao)
        dados = await consultas.resumo(porta, usuario, filtros)
    return _resumo_out(dados)


def _resumo_out(dados: consultas.Resumo) -> ResumoOut:
    def da_categoria(nome: str) -> list[ItemDistribuicaoOut]:
        return [
            ItemDistribuicaoOut(
                chave=str(linha["chave"]),
                rotulo=str(linha["rotulo"]),
                quantidade=int(str(linha["quantidade"])),
            )
            for linha in dados.categorias
            if linha["categoria"] == nome
        ]

    q = dados.qualidade
    return ResumoOut(
        unidades=UnidadesResumoOut(
            total=int(str(q["total_units"])),
            por_status={i.chave: i.quantidade for i in da_categoria("status")},
            por_tipo=da_categoria("tipo"),
            por_area=da_categoria("area"),
            por_distrito=da_categoria("distrito"),
            por_situacao_cadastral={
                i.chave: i.quantidade for i in da_categoria("situacao_cadastral")
            },
        ),
        qualidade=QualidadeOut(
            unidades_com_pendencias=int(str(q["units_with_issues"])),
            total_pendencias=int(str(q["total_issues"])),
            sem_cnes=int(str(q["units_without_cnes"])),
            servicos_fora_cnes=int(str(q["services_outside_cnes"])),
        ),
        alteracoes=AlteracoesResumoOut(
            ultimos_7_dias=int(str(dados.alteracoes["last_7_days"])),
            ultimos_30_dias=int(str(dados.alteracoes["last_30_days"])),
            recentes=[AlteracaoRecenteOut.model_validate(linha) for linha in dados.recentes],
        ),
        gerado_em=agora_em_recife(),
    )
