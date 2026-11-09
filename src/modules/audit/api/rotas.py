"""Rotas da trilha de auditoria (spec 008) e do log do banco (spec 011, T14 e T15)."""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request

from src.core.paginacao import TAMANHO_PADRAO, NumeroDaPagina, PaginaOut, TamanhoDaPagina
from src.core.problem import PROBLEM_JSON
from src.modules.access.api.deps import ResourceRef, UsuarioAtual, require
from src.modules.audit.api.schemas import (
    EventoDetalheOut,
    EventoOut,
    ParticaoOut,
    RegistroDoBancoOut,
    VerificacaoIn,
    VerificacaoOut,
)
from src.modules.audit.application import consultar
from src.modules.audit.application.consultar import (
    ConsultasDeAuditoria,
    FiltrosDeEventos,
    FiltrosDeHistorico,
    FiltrosDoLogDoBanco,
    Pagina,
)

_ERROS: dict[int | str, dict[str, Any]] = {
    401: {"description": "Sem access token válido", "content": {PROBLEM_JSON: {}}},
    403: {"description": "Sem `auditoria:read` no escopo pedido", "content": {PROBLEM_JSON: {}}},
}

router = APIRouter(prefix="/api/v1", tags=["auditoria"], responses=_ERROS)

Auditor = Annotated[UsuarioAtual, Depends(require(consultar.LEITURA))]
AuditorDaUnidade = Annotated[
    UsuarioAtual, Depends(require(consultar.LEITURA, ResourceRef("unidade")))
]


def _porta(request: Request, sessao: Any) -> ConsultasDeAuditoria:
    porta: ConsultasDeAuditoria = request.app.state.consultas_auditoria(sessao)
    return porta


@router.get(
    "/unidades/{id}/historico",
    summary="Histórico da unidade (vw_unit_history)",
    responses={404: {"description": "Unidade inexistente", "content": {PROBLEM_JSON: {}}}},
)
async def historico(
    request: Request,
    id: UUID,
    usuario: AuditorDaUnidade,
    de: datetime | None = None,
    ate: datetime | None = None,
    autor: UUID | None = None,
    campo: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    pagina: NumeroDaPagina = 1,
    tamanho: TamanhoDaPagina = TAMANHO_PADRAO,
) -> PaginaOut[EventoOut]:
    """008/R1; 011/R4.5: eventos da unidade, de seus equipamentos e serviços, mais recentes
    primeiro, com autor, papel e `{campo, de, para}` rotulados."""
    async with request.app.state.sessoes() as sessao:
        resultado = await consultar.historico_da_unidade(
            id,
            FiltrosDeHistorico(de=de, ate=ate, autor=autor, campo=campo),
            Pagina(pagina, tamanho),
            consultas=_porta(request, sessao),
        )
    return PaginaOut(
        itens=[EventoOut.de(e) for e in resultado.itens],
        total=resultado.total,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.get("/auditoria/eventos", summary="Trilha geral de auditoria")
async def eventos(
    request: Request,
    usuario: Auditor,
    de: datetime | None = None,
    ate: datetime | None = None,
    acao: Annotated[str | None, Query(max_length=100, description="Prefixo da ação.")] = None,
    entidade_tipo: Annotated[str | None, Query(max_length=50)] = None,
    entidade_id: Annotated[str | None, Query(max_length=100)] = None,
    autor: UUID | None = None,
    pagina: NumeroDaPagina = 1,
    tamanho: TamanhoDaPagina = TAMANHO_PADRAO,
) -> PaginaOut[EventoOut]:
    """008/R2.1, R2.2: escopo global; `auth.*` e `acesso.negado` só com
    `auditoria:read_acessos`."""
    async with request.app.state.sessoes() as sessao:
        resultado = await consultar.listar_eventos(
            usuario,
            FiltrosDeEventos(
                de=de,
                ate=ate,
                acao=acao,
                entidade_tipo=entidade_tipo,
                entidade_id=entidade_id,
                autor=autor,
            ),
            Pagina(pagina, tamanho),
            consultas=_porta(request, sessao),
        )
    return PaginaOut(
        itens=[EventoOut.de(e) for e in resultado.itens],
        total=resultado.total,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.get(
    "/auditoria/eventos/{id_}",
    summary="Evento da trilha com hash",
    responses={404: {"description": "Evento inexistente", "content": {PROBLEM_JSON: {}}}},
)
async def evento(
    request: Request, id_: Annotated[int, Path(ge=1)], usuario: Auditor
) -> EventoDetalheOut:
    """008/R3.2."""
    async with request.app.state.sessoes() as sessao:
        item = await consultar.detalhar_evento(usuario, id_, consultas=_porta(request, sessao))
    return EventoDetalheOut.do_evento(item)


@router.post("/auditoria/verificar", summary="Verificar a integridade da cadeia de hash")
async def verificar(request: Request, corpo: VerificacaoIn, usuario: Auditor) -> VerificacaoOut:
    """008/R3.1: recalcula a cadeia (só leitura) e responde `integra` ou o primeiro evento que
    quebra."""
    async with request.app.state.sessoes() as sessao:
        resultado = await consultar.verificar_cadeia(
            usuario, corpo.de, corpo.ate, consultas=_porta(request, sessao)
        )
    return VerificacaoOut.de(resultado)


@router.get("/auditoria/banco", summary="Log do banco (trigger trg_registry_change_log)")
async def log_do_banco(
    request: Request,
    usuario: Auditor,
    de: datetime | None = None,
    ate: datetime | None = None,
    tabela: Literal["health_units", "equipments", "services"] | None = None,
    fora_da_api: bool = False,
    pagina: NumeroDaPagina = 1,
    tamanho: TamanhoDaPagina = TAMANHO_PADRAO,
) -> PaginaOut[RegistroDoBancoOut]:
    """011/R7.7, R7.8: toda escrita no cadastro, inclusive fora da API; escopo global."""
    async with request.app.state.sessoes() as sessao:
        resultado = await consultar.log_do_banco(
            usuario,
            FiltrosDoLogDoBanco(de=de, ate=ate, tabela=tabela, fora_da_api=fora_da_api),
            Pagina(pagina, tamanho),
            consultas=_porta(request, sessao),
        )
    return PaginaOut(
        itens=[RegistroDoBancoOut.de(r) for r in resultado.itens],
        total=resultado.total,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.get("/auditoria/banco/particoes", summary="Partições mensais do log do banco")
async def particoes(request: Request, usuario: Auditor) -> list[ParticaoOut]:
    """011/R6.9: efeito do procedimento com cursor `sp_ensure_monthly_partitions`."""
    async with request.app.state.sessoes() as sessao:
        itens = await consultar.particoes(usuario, consultas=_porta(request, sessao))
    return [ParticaoOut.de(p) for p in itens]
