"""Dependências de autorização das rotas (spec 003, design § Verificação).

Toda rota de /api/v1 que não seja pública declara a permissão com `require()` (R4.1):

    @router.get("/coisas", dependencies=[Depends(require("coisa:read"))])

ou, quando o handler precisa do usuário e das permissões dele:

    async def handler(usuario: Annotated[UsuarioAtual, Depends(require("coisa:read"))]): ...

Quando a permissão depende do recurso da rota (R4.3), `ResourceRef` diz o tipo dele e o
parâmetro de caminho com o id:

    @router.patch("/unidades/{id}", dependencies=[Depends(require("unidade:update",
                                                                   ResourceRef("unidade")))])

A dependência autentica pelo `CurrentUser` da 002 (401) e confere a permissão nas permissões
efetivas do usuário, lidas a cada requisição (403). O 403 é auditado como `acesso.negado`.

Rotas que leem ou gravam dados de negócio recebem a sessão da requisição por `SessaoDeNegocio`,
declarada depois do `require` (padrão da 006/T3, para as rotas da 006 e da 011):

    async def handler(
        request: Request,
        usuario: Annotated[UsuarioAtual, Depends(require("unidade:create"))],
        sessao: SessaoDeNegocio,
    ):
        estado = request.app.state
        await caso_de_uso(..., repositorio=estado.repositorio_de_x(sessao),
                          auditoria=estado.auditoria(sessao),
                          ator=ator_da_requisicao(request, usuario))

Uma sessão e uma transação por requisição: o caso de uso e o `audit.registrar` gravam juntos, e
a transação é confirmada quando o handler termina, antes de a resposta sair (`scope="function"`).
Qualquer exceção desfaz tudo. Um `AcessoNegado` levantado pelo caso de uso (uma regra de escopo
que só se confere depois de ler o corpo ou o banco) é auditado depois do rollback, numa
transação própria, como o do `require`.
"""

import contextlib
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated, Any, Protocol
from uuid import UUID

import structlog
from fastapi import Depends, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.errors import (
    AppError,
    Conflict,
    DomainValidationError,
    PreconditionFailed,
    PreconditionRequired,
)
from src.core.origem import origem_da_requisicao
from src.modules.access.application.autorizacao import (
    AcessoNegado,
    Ator,
    AuditStore,
    Entidade,
    Recurso,
    RepositorioDePermissoes,
    ResolvedorDeAlvo,
    ResolvedorDePermissoes,
    UsuarioAtual,
    auditar_negacao,
    registrar_falha,
    verificar,
)
from src.modules.identity.api.deps import CurrentUser

__all__ = [
    "Autenticado",
    "ResourceRef",
    "SessaoDeNegocio",
    "UsuarioAtual",
    "ator_da_requisicao",
    "require",
]


@dataclass(frozen=True)
class ResourceRef:
    """O recurso da rota cujo escopo a permissão confere (design § Verificação).

    `tipo` escolhe o `ResolvedorDeAlvo` registrado em `app.state.resolvedores_de_alvo` e vai
    para a auditoria (`entity_type`); `parametro` é o parâmetro de caminho que traz o id.
    """

    tipo: str
    parametro: str = "id"


class _Exigencia:
    """A dependência que `require()` devolve. Guarda a permissão e o recurso, para quem
    inspeciona as rotas (teste de rotas protegidas, 003/T5)."""

    def __init__(self, permissao: str, recurso: ResourceRef | None) -> None:
        self.permissao = permissao
        self.recurso = recurso

    def __repr__(self) -> str:
        return f"require({self.permissao!r}, {self.recurso!r})"

    async def __call__(self, request: Request, usuario: CurrentUser) -> UsuarioAtual:
        estado = request.app.state
        resolvedor: ResolvedorDePermissoes = estado.resolvedor_de_permissoes
        recurso = self._recurso_pedido(request)
        try:
            async with estado.sessoes() as sessao:
                repositorio: RepositorioDePermissoes = estado.repositorio_de_permissoes(sessao)
                alvos: ResolvedorDeAlvo | None = (
                    None if recurso is None else estado.resolvedores_de_alvo[recurso.tipo](sessao)
                )
                return await verificar(
                    resolvedor,
                    repositorio,
                    usuario_id=usuario.id,
                    sessao_id=usuario.sessao_id,
                    permissao=self.permissao,
                    recurso=recurso,
                    alvos=alvos,
                )
        except AcessoNegado as negacao:
            await _auditar_em_transacao_propria(request, usuario, negacao)
            raise

    def _recurso_pedido(self, request: Request) -> Recurso | None:
        if self.recurso is None:
            return None
        return Recurso(tipo=self.recurso.tipo, id=request.path_params[self.recurso.parametro])


def require(permissao: str, recurso: ResourceRef | None = None) -> Any:
    """Dependência que exige `permissao` do usuário autenticado, no escopo do `recurso` se houver,
    e devolve o `UsuarioAtual`."""
    return _Exigencia(permissao, recurso)


class _Autenticacao:
    """Dependência das rotas que só exigem estar autenticado (`GET /me`, 003/R5.1): carrega as
    permissões efetivas sem exigir nenhuma. O teste de rotas protegidas (003/T5) a reconhece."""

    def __repr__(self) -> str:
        return "autenticado()"

    async def __call__(self, request: Request, usuario: CurrentUser) -> UsuarioAtual:
        estado = request.app.state
        resolvedor: ResolvedorDePermissoes = estado.resolvedor_de_permissoes
        async with estado.sessoes() as sessao:
            repositorio: RepositorioDePermissoes = estado.repositorio_de_permissoes(sessao)
            permissoes, papeis = await resolvedor.resolver(repositorio, usuario.id)
        return UsuarioAtual(
            id=usuario.id, sessao_id=usuario.sessao_id, permissoes=permissoes, papeis=papeis
        )


autenticado = _Autenticacao()
Autenticado = Annotated[UsuarioAtual, Depends(autenticado)]
"""O usuário autenticado com as permissões efetivas, sem exigir permissão nenhuma."""


async def _sessao_de_negocio(request: Request, usuario: CurrentUser) -> AsyncIterator[Any]:
    """013/R4.3 a R4.8: as falhas selecionadas viram `operacao.falhou`, gravado depois do
    rollback numa transação própria. A ordem dos `except` importa: `AcessoNegado` (um `Forbidden`)
    primeiro; depois os selecionados; os demais erros HTTP e de aplicação (401, 403 comum, 404,
    429, 422 de schema) passam sem registro; só o que sobra é erro interno (500). Em todos os
    casos sai o mesmo erro original."""
    estado = request.app.state
    try:
        async with estado.sessoes() as sessao, sessao.begin():
            yield sessao
    except AcessoNegado as negacao:
        # Depois do rollback: a transação desfeita não segura trava que o registro precise.
        await _auditar_em_transacao_propria(request, usuario, negacao)
        raise
    except _SELECIONADOS as erro:
        await _registrar_falha_sem_mascarar(request, usuario, erro, codigo=_codigo(erro))
        raise
    except (AppError, StarletteHTTPException, RequestValidationError):
        raise
    except Exception as erro:
        await _registrar_falha_sem_mascarar(request, usuario, erro, codigo="erro_interno")
        raise


_SELECIONADOS = (Conflict, PreconditionFailed, PreconditionRequired, DomainValidationError)
_CODIGOS: tuple[tuple[type[AppError], str], ...] = (
    (Conflict, "conflito"),
    (PreconditionFailed, "precondicao_falhou"),
    (PreconditionRequired, "precondicao_ausente"),
    (DomainValidationError, "validacao_dominio"),
)
_log_de_erro = structlog.get_logger("sgs_api.erro")


def _codigo(erro: AppError) -> str:
    return next(codigo for classe, codigo in _CODIGOS if isinstance(erro, classe))


async def _registrar_falha_sem_mascarar(
    request: Request, usuario: "_Identificado", erro: Exception, *, codigo: str
) -> None:
    """Grava `operacao.falhou` (013/R4.3) numa sessão e transação próprias, depois do rollback
    da operação. Só em escrita e uma vez por requisição (R4.7). Se a gravação falhar, fica só o
    log técnico, sem valores, e quem sai é o erro original (R4.8)."""
    if request.method not in _ESCRITA or getattr(erro, "auditada", False):
        return
    status = int(getattr(type(erro), "status", 500)) if codigo != "erro_interno" else 500
    rota = _template(request)
    try:
        estado = request.app.state
        async with estado.sessoes() as sessao, sessao.begin():
            await registrar_falha(
                estado.auditoria(sessao),
                ator=ator_da_requisicao(request, usuario),
                metodo=request.method,
                rota=rota,
                status=status,
                codigo=codigo,
                campos=[e.campo for e in getattr(erro, "errors", ())],
                entidade=_entidade_do_caminho(request),
            )
    except Exception:
        _log_de_erro.error(
            "auditoria_falha_nao_registrada",
            rota=rota,
            status=status,
            codigo=codigo,
            request_id=getattr(request.state, "request_id", None),
        )
        return
    with contextlib.suppress(AttributeError):  # exceção que não aceita atributo
        erro.auditada = True  # type: ignore[attr-defined]


_ESCRITA = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_TIPO_DE_REFERENCIA = re.compile(r"[a-z_]{1,40}")


def _template(request: Request) -> str:
    caminho = getattr(request.scope.get("route"), "path", None)
    return caminho if isinstance(caminho, str) else "/"


def _entidade_do_caminho(request: Request) -> Entidade | None:
    """A entidade da falha (013/R4.4), só quando o caminho a identifica sem ambiguidade: o tipo
    vem do template da rota, e o id precisa ter o formato certo. Sem id no caminho (por exemplo,
    `POST /unidades`), nenhuma entidade."""
    rota = _template(request)
    parametros = request.path_params

    def uuid_de(nome: str) -> str | None:
        valor = str(parametros.get(nome, ""))
        return valor.lower() if _UUID.fullmatch(valor) else None

    if rota.startswith("/api/v1/unidades/{id}") and (id_ := uuid_de("id")):
        return Entidade(tipo="unidade", id=id_)
    if rota.startswith("/api/v1/equipamentos/{equipamento_id}") and (
        id_ := uuid_de("equipamento_id")
    ):
        return Entidade(tipo="equipamento", id=id_)
    if rota.startswith("/api/v1/servicos/{servico_id}") and (id_ := uuid_de("servico_id")):
        return Entidade(tipo="servico", id=id_)
    if rota == "/api/v1/admin/atribuicoes/{id_}" and (id_ := uuid_de("id_")):
        return Entidade(tipo="atribuicao", id=id_)
    if rota == "/api/v1/referencias/{tipo}/{id_}":
        tipo, ident = str(parametros.get("tipo", "")), str(parametros.get("id_", ""))
        if _TIPO_DE_REFERENCIA.fullmatch(tipo) and ident.isdigit():
            return Entidade(tipo="referencia", id=f"{tipo}:{ident}")
    return None


SessaoDeNegocio = Annotated[Any, Depends(_sessao_de_negocio, scope="function")]
"""A sessão SQLAlchemy da requisição, já dentro da transação de negócio (ver o docstring do
módulo). Os repositórios de `app.state` a recebem; o tipo fica opaco para a camada api."""


class _Identificado(Protocol):
    @property
    def id(self) -> UUID: ...

    @property
    def sessao_id(self) -> UUID: ...


def ator_da_requisicao(request: Request, usuario: _Identificado) -> Ator:
    """Quem faz a requisição e de onde, para a auditoria (001/R5.1). A requisição autenticada é
    sempre de um usuário, vinda da API (013/R1.1); tipo e origem não vêm do cliente."""
    origem = origem_da_requisicao(request)
    return Ator(
        tipo="usuario",
        origem=ORIGEM_API,
        user_id=usuario.id,
        papeis=tuple(getattr(usuario, "papeis", ())),
        session_id=usuario.sessao_id,
        ip=origem.ip,
        user_agent=origem.user_agent,
        request_id=origem.request_id,
    )


ORIGEM_API = "api"
"""Rótulo de origem dos eventos gravados pelas rotas da API (013/R1.1)."""


async def _auditar_em_transacao_propria(
    request: Request, usuario: _Identificado, negacao: AcessoNegado
) -> None:
    """Grava `acesso.negado` (003/R4.6) numa transação só dele, que o 403 não desfaz. Uma
    negação já registrada (do `require`, que pode passar pela `SessaoDeNegocio`) não repete."""
    if negacao.auditada:
        return
    estado = request.app.state
    async with estado.sessoes() as sessao, sessao.begin():
        store: AuditStore = estado.auditoria(sessao)
        await auditar_negacao(
            store, negacao, ator=ator_da_requisicao(request, usuario), rota=_rota(request)
        )
    negacao.auditada = True


def _rota(request: Request) -> str:
    """Método e rota como declarada (ex.: `PATCH /api/v1/unidades/{id}`), sem valores."""
    caminho = getattr(request.scope.get("route"), "path", request.url.path)
    return f"{request.method} {caminho}"
