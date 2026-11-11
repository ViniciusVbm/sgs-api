"""Casos de uso da consulta da trilha (spec 008) e do log do banco (spec 011, T15).

O histórico de uma unidade tem o escopo conferido pela rota (`auditoria:read` no escopo da
unidade). A trilha geral, o log do banco e as partições exigem `auditoria:read` com escopo
global; os eventos de acesso, `auditoria:read_acessos` (008/R2.2).
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from src.core.errors import NotFound
from src.modules.access.application.autorizacao import UsuarioAtual, exigir_escopo_global
from src.modules.access.domain.authorization import pode
from src.modules.audit.domain.consultas import (
    Ancora,
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
    "EVENTO_CONSULTADO",
    "Ancora",
    "AncoraGerada",
    "ConsultasDeAuditoria",
    "Evento",
    "FiltrosDeEventos",
    "FiltrosDeHistorico",
    "FiltrosDoLogDoBanco",
    "Pagina",
    "Particao",
    "RegistrarConsulta",
    "RegistrarExecucao",
    "RegistroDoBanco",
    "Resultado",
    "ResultadoDaVerificacao",
    "detalhar_evento",
    "gerar_ancora",
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


EVENTO_CONSULTADO = "auditoria.evento_consultado"
"""013/R7.4: quem viu o detalhe de qual evento. É evento de acesso: o Gestor de Dados não deve
descobrir a investigação do Auditor."""

RegistrarConsulta = Callable[[int], Awaitable[None]]
"""Grava `auditoria.evento_consultado` do evento visto, na transação da consulta (013/R7.4)."""


def _e_de_acesso(acao: str) -> bool:
    return acao.startswith("auth.") or acao in {"acesso.negado", EVENTO_CONSULTADO}


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
    usuario: UsuarioAtual,
    id_: int,
    *,
    consultas: ConsultasDeAuditoria,
    registrar_consulta: RegistrarConsulta | None = None,
) -> Evento:
    """008/R3.2: com `hash` e `prev_hash`. Evento de acesso sem a permissão de acessos é 404,
    para não revelar que ele existe.

    013/R8.2: IP, User-Agent e sessão só com `auditoria:read_acessos`; para os demais vêm nulos,
    com `origem_restrita`. 013/R7.4: a consulta que encontra o evento grava
    `auditoria.evento_consultado` (só o id visto)."""
    exigir_escopo_global(usuario, LEITURA)
    evento = await consultas.evento(id_)
    ve_acessos = pode(usuario.permissoes, ACESSOS)
    if evento is None or (_e_de_acesso(evento.action) and not ve_acessos):
        raise NotFound("Evento não encontrado.")
    if not ve_acessos:
        evento = replace(evento, ip=None, user_agent=None, session_id=None, origem_restrita=True)
    if registrar_consulta is not None:
        await registrar_consulta(id_)
    return evento


RegistrarExecucao = Callable[[ResultadoDaVerificacao], Awaitable[None]]
"""Grava `auditoria.verificada` (013/R7.3) numa transação própria. A API passa uma; a verificação
offline (013/T9) não passa nenhuma e não grava nada."""


async def verificar_cadeia(
    usuario: UsuarioAtual,
    de: datetime | None,
    ate: datetime | None,
    *,
    consultas: ConsultasDeAuditoria,
    registrar_execucao: RegistrarExecucao | None = None,
    ancora: Ancora | None = None,
) -> ResultadoDaVerificacao:
    """008/R3.1; 013/R5.1, R5.2, R5.5, R5.11, R7.3.

    Recalcula a cadeia em lotes, em ordem de id, numa foto única do banco (REPEATABLE READ, READ
    ONLY): a cabeça e todos os lotes são lidos na mesma foto, então um evento gravado durante a
    verificação não é visto e não gera falso "fim não confere"; ele entra na verificação seguinte.
    Aponta o primeiro evento cujo `prev_hash` não é o hash do anterior ou cujo conteúdo não confere
    com o hash. Sem período, o hash do último evento lido precisa ser o `last_hash` da cabeça
    (remoção no fim). Com `ancora` (013/R5.3), confere também, na mesma foto, se a cadeia é a da
    âncora (hash do primeiro evento) e se o evento ancorado ainda tem o hash guardado. Depois da
    leitura, `registrar_execucao` grava o resultado, se houver."""
    exigir_escopo_global(usuario, LEITURA)
    await consultas.fixar_foto_consistente()
    cabeca = await consultas.cabeca_da_cadeia() if de is None and ate is None else None
    resultado = await _percorrer(consultas, de, ate, cabeca)
    if ancora is not None:
        resultado = await _conferir_ancora(consultas, ancora, resultado)
    if registrar_execucao is not None:
        await registrar_execucao(resultado)
    return resultado


async def _conferir_ancora(
    consultas: ConsultasDeAuditoria, ancora: Ancora, resultado: ResultadoDaVerificacao
) -> ResultadoDaVerificacao:
    identidade = await consultas.identidade_da_cadeia()
    cadeia_confere = identidade.cadeia_id == ancora.cadeia_id
    ancora_confere = await consultas.hash_do_evento(ancora.id) == ancora.hash
    motivo = resultado.motivo
    if motivo is None and not cadeia_confere:
        motivo = "a cadeia não é a da âncora (o primeiro evento mudou)"
    elif motivo is None and not ancora_confere:
        motivo = "a âncora não confere (o evento ancorado sumiu ou mudou)"
    return replace(
        resultado,
        integra=resultado.integra and cadeia_confere and ancora_confere,
        motivo=motivo,
        cadeia_confere=cadeia_confere,
        ancora_confere=ancora_confere,
    )


@dataclass(frozen=True, slots=True)
class AncoraGerada:
    """013/R5.4: o conteúdo da âncora, versão 1, sem dado pessoal (R5.9)."""

    cadeia_id: str
    id: int
    hash: str
    total: int
    banco: str
    versao: int = 1


async def gerar_ancora(
    usuario: UsuarioAtual, *, consultas: ConsultasDeAuditoria
) -> tuple[ResultadoDaVerificacao, AncoraGerada | None]:
    """013/R5.4: verifica a cadeia inteira (a mesma verificação, sem gravar nada) e, se estiver
    íntegra e não vazia, devolve a âncora do último evento verificado, com o total e o
    `cadeia_id` lidos na mesma foto. Cadeia vazia ou divergente: sem âncora."""
    resultado = await verificar_cadeia(usuario, None, None, consultas=consultas)
    if not resultado.integra or resultado.ultimo_id is None or resultado.hash_final is None:
        return resultado, None
    identidade = await consultas.identidade_da_cadeia()
    if identidade.cadeia_id is None:  # pragma: no cover - há eventos verificados
        return resultado, None
    return resultado, AncoraGerada(
        cadeia_id=identidade.cadeia_id,
        id=resultado.ultimo_id,
        hash=resultado.hash_final,
        total=identidade.total,
        banco=identidade.banco,
    )


async def _percorrer(
    consultas: ConsultasDeAuditoria, de: datetime | None, ate: datetime | None, cabeca: str | None
) -> ResultadoDaVerificacao:
    verificados = 0
    ultimo_id: int | None = None
    anterior: str | None = None
    while True:
        lote = await consultas.lote_da_cadeia(ultimo_id or 0, de, ate, LOTE)
        if not lote:
            break
        for id_, entrada in lote:
            if anterior is None:
                anterior = await consultas.hash_anterior(id_) or GENESIS_HASH
            motivo = None
            if entrada.prev_hash != anterior:
                motivo = "prev_hash não é o hash do evento anterior"
            elif entrada.recompute_hash() != entrada.hash:
                motivo = "o conteúdo não confere com o hash gravado"
            if motivo is not None:
                return ResultadoDaVerificacao(
                    integra=False,
                    verificados=verificados,
                    primeiro_evento_divergente=id_,
                    motivo=motivo,
                    ultimo_id=ultimo_id,
                    hash_final=anterior if ultimo_id is not None else None,
                )
            anterior = entrada.hash
            verificados += 1
            ultimo_id = id_
    hash_final = anterior if ultimo_id is not None else None
    if cabeca is None:
        return ResultadoDaVerificacao(
            integra=True, verificados=verificados, ultimo_id=ultimo_id, hash_final=hash_final
        )
    cabeca_confere = (hash_final or GENESIS_HASH) == cabeca
    return ResultadoDaVerificacao(
        integra=cabeca_confere,
        verificados=verificados,
        motivo=None if cabeca_confere else "o fim da cadeia não confere com audit_chain_head",
        ultimo_id=ultimo_id,
        hash_final=hash_final,
        cabeca_confere=cabeca_confere,
    )


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
