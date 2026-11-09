"""Casos de uso da consulta da trilha (spec 008) e do log do banco (spec 011, T15).

O histórico de uma unidade tem o escopo conferido pela rota (`auditoria:read` no escopo da
unidade). A trilha geral, o log do banco e as partições exigem `auditoria:read` com escopo
global; os eventos de acesso, `auditoria:read_acessos` (008/R2.2).
"""

from datetime import datetime
from uuid import UUID

from src.core.errors import NotFound
from src.modules.access.application.autorizacao import UsuarioAtual, exigir_escopo_global
from src.modules.access.domain.authorization import pode
from src.modules.audit.domain.consultas import (
    Evento,
    FiltrosDeEventos,
    FiltrosDeHistorico,
    FiltrosDoLogDoBanco,
    Pagina,
    Particao,
    RegistroDoBanco,
    Resultado,
    ResultadoDaVerificacao,
    rotulo,
)
from src.modules.audit.domain.entry import GENESIS_HASH
from src.modules.audit.domain.ports import ConsultasDeAuditoria

__all__ = [
    "ConsultasDeAuditoria",
    "Evento",
    "FiltrosDeEventos",
    "FiltrosDeHistorico",
    "FiltrosDoLogDoBanco",
    "Pagina",
    "Particao",
    "RegistroDoBanco",
    "Resultado",
    "ResultadoDaVerificacao",
    "detalhar_evento",
    "historico_da_unidade",
    "listar_eventos",
    "log_do_banco",
    "particoes",
    "rotulo",
    "verificar_cadeia",
]

LEITURA = "auditoria:read"
ACESSOS = "auditoria:read_acessos"
LOTE = 1000


def _e_de_acesso(acao: str) -> bool:
    return acao.startswith("auth.") or acao == "acesso.negado"


async def historico_da_unidade(
    unidade_id: UUID,
    filtros: FiltrosDeHistorico,
    pagina: Pagina,
    *,
    consultas: ConsultasDeAuditoria,
) -> Resultado[Evento]:
    """008/R1.1 a R1.3; 011/R4.5: pela `vw_unit_history`."""
    return await consultas.historico_da_unidade(unidade_id, filtros, pagina)


async def listar_eventos(
    usuario: UsuarioAtual,
    filtros: FiltrosDeEventos,
    pagina: Pagina,
    *,
    consultas: ConsultasDeAuditoria,
) -> Resultado[Evento]:
    """008/R2.1, R2.2: trilha geral, global; eventos de acesso só com `auditoria:read_acessos`."""
    exigir_escopo_global(usuario, LEITURA)
    return await consultas.eventos(
        filtros, pagina, incluir_acessos=pode(usuario.permissoes, ACESSOS)
    )


async def detalhar_evento(
    usuario: UsuarioAtual, id_: int, *, consultas: ConsultasDeAuditoria
) -> Evento:
    """008/R3.2: com `hash` e `prev_hash`. Evento de acesso sem a permissão de acessos é 404,
    para não revelar que ele existe."""
    exigir_escopo_global(usuario, LEITURA)
    evento = await consultas.evento(id_)
    if evento is None or (_e_de_acesso(evento.action) and not pode(usuario.permissoes, ACESSOS)):
        raise NotFound("Evento não encontrado.")
    return evento


async def verificar_cadeia(
    usuario: UsuarioAtual,
    de: datetime | None,
    ate: datetime | None,
    *,
    consultas: ConsultasDeAuditoria,
) -> ResultadoDaVerificacao:
    """008/R3.1: recalcula a cadeia em lotes, em ordem de id, e aponta o primeiro evento cujo
    hash não confere com o conteúdo ou cujo `prev_hash` não é o hash do anterior. Só leitura."""
    exigir_escopo_global(usuario, LEITURA)
    verificados = 0
    ultimo_id = 0
    anterior: str | None = None
    while True:
        lote = await consultas.lote_da_cadeia(ultimo_id, de, ate, LOTE)
        if not lote:
            break
        for id_, entrada in lote:
            if anterior is None:
                anterior = await consultas.hash_anterior(id_) or GENESIS_HASH
            if entrada.prev_hash != anterior:
                return ResultadoDaVerificacao(
                    integra=False,
                    verificados=verificados,
                    primeiro_evento_divergente=id_,
                    motivo="prev_hash não é o hash do evento anterior",
                )
            if entrada.recompute_hash() != entrada.hash:
                return ResultadoDaVerificacao(
                    integra=False,
                    verificados=verificados,
                    primeiro_evento_divergente=id_,
                    motivo="o conteúdo não confere com o hash gravado",
                )
            anterior = entrada.hash
            verificados += 1
            ultimo_id = id_
    return ResultadoDaVerificacao(integra=True, verificados=verificados)


async def log_do_banco(
    usuario: UsuarioAtual,
    filtros: FiltrosDoLogDoBanco,
    pagina: Pagina,
    *,
    consultas: ConsultasDeAuditoria,
) -> Resultado[RegistroDoBanco]:
    """011/R7.7, R7.8: só com escopo global de `auditoria:read`."""
    exigir_escopo_global(usuario, LEITURA)
    return await consultas.log_do_banco(filtros, pagina)


async def particoes(usuario: UsuarioAtual, *, consultas: ConsultasDeAuditoria) -> list[Particao]:
    """011/R6.9."""
    exigir_escopo_global(usuario, LEITURA)
    return await consultas.particoes()
