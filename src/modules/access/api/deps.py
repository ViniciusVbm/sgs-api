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
"""

import ipaddress
from dataclasses import dataclass
from typing import Any

from fastapi import Request

from src.modules.access.application.autorizacao import (
    AcessoNegado,
    Ator,
    AuditStore,
    Recurso,
    RepositorioDePermissoes,
    ResolvedorDeAlvo,
    ResolvedorDePermissoes,
    UsuarioAtual,
    auditar_negacao,
    verificar,
)
from src.modules.identity.api.deps import CurrentUser

__all__ = ["ResourceRef", "UsuarioAtual", "require"]


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
            ator = Ator(
                user_id=usuario.id,
                session_id=usuario.sessao_id,
                ip=_ip(request),
                request_id=getattr(request.state, "request_id", None),
            )
            async with estado.sessoes() as sessao, sessao.begin():
                store: AuditStore = estado.auditoria(sessao)
                await auditar_negacao(store, negacao, ator=ator, rota=_rota(request))
            raise

    def _recurso_pedido(self, request: Request) -> Recurso | None:
        if self.recurso is None:
            return None
        return Recurso(tipo=self.recurso.tipo, id=request.path_params[self.recurso.parametro])


def require(permissao: str, recurso: ResourceRef | None = None) -> Any:
    """Dependência que exige `permissao` do usuário autenticado, no escopo do `recurso` se houver,
    e devolve o `UsuarioAtual`."""
    return _Exigencia(permissao, recurso)


def _rota(request: Request) -> str:
    """Método e rota como declarada (ex.: `PATCH /api/v1/unidades/{id}`), sem valores."""
    caminho = getattr(request.scope.get("route"), "path", request.url.path)
    return f"{request.method} {caminho}"


def _ip(request: Request) -> str | None:
    """IP do cliente, se for um IP (um cliente de teste pode se apresentar com um nome)."""
    host = request.client.host if request.client else None
    try:
        return str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        return None
