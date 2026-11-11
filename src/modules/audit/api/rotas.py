"""Rotas da trilha de auditoria (spec 008) e do log do banco (spec 011, T14 e T15)."""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request

from src.core.paginacao import TAMANHO_PADRAO, NumeroDaPagina, PaginaOut, TamanhoDaPagina
from src.core.problem import PROBLEM_JSON
from src.modules.access.api.deps import ResourceRef, UsuarioAtual, ator_da_requisicao, require
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
    ResultadoDaVerificacao,
)
from src.modules.audit.application.registrar import Entidade, registrar

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
    """008/R3.2; 013/R7.4, R8.2: IP, User-Agent e sessão só com `auditoria:read_acessos`; a
    consulta grava `auditoria.evento_consultado`, na mesma transação."""
    estado = request.app.state
    async with estado.sessoes() as sessao, sessao.begin():

        async def registrar_consulta(consultado: int) -> None:
            await registrar(
                estado.auditoria(sessao),
                acao=consultar.EVENTO_CONSULTADO,
                ator=ator_da_requisicao(request, usuario),
                entidade=Entidade(tipo="evento_auditoria", id=str(consultado)),
            )

        item = await consultar.detalhar_evento(
            usuario, id_, consultas=_porta(request, sessao), registrar_consulta=registrar_consulta
        )
    return EventoDetalheOut.do_evento(item)


@router.post("/auditoria/verificar", summary="Verificar a integridade da cadeia de hash")
async def verificar(request: Request, corpo: VerificacaoIn, usuario: Auditor) -> VerificacaoOut:
    """008/R3.1; 013/R5.1, R5.5, R5.11, R7.3: recalcula a cadeia numa transação REPEATABLE READ,
    READ ONLY, compara o fim com a cabeça e responde `integra` ou o primeiro evento que quebra. O
    `auditoria.verificada` vai numa sessão e transação próprias, fora da de leitura."""

    async def registrar_execucao(resultado: ResultadoDaVerificacao) -> None:
        estado = request.app.state
        async with estado.sessoes() as sessao, sessao.begin():
            await registrar(
                estado.auditoria(sessao),
                acao="auditoria.verificada",
                ator=ator_da_requisicao(request, usuario),
                metadados={
                    "integra": resultado.integra,
                    "verificados": resultado.verificados,
                    "ultimo_id": resultado.ultimo_id,
                    "cabeca_confere": resultado.cabeca_confere,
                    "cadeia_confere": resultado.cadeia_confere,
                    "ancora_confere": resultado.ancora_confere,
                    "primeiro_evento_divergente": resultado.primeiro_evento_divergente,
                },
            )

    async with request.app.state.sessoes() as sessao:
        resultado = await consultar.verificar_cadeia(
            usuario,
            corpo.de,
            corpo.ate,
            consultas=_porta(request, sessao),
            registrar_execucao=registrar_execucao,
            ancora=corpo.ancora.para_dominio() if corpo.ancora else None,
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
