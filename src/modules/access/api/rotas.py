"""`GET /me` e administração de papéis e atribuições (spec 003, design § Rotas; T6 e T7)."""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from src.core.ids import uuid7
from src.core.problem import PROBLEM_JSON
from src.modules.access.api.deps import (
    Autenticado,
    SessaoDeNegocio,
    UsuarioAtual,
    ator_da_requisicao,
    require,
)
from src.modules.access.application import atribuicoes as casos

router = APIRouter(prefix="/api/v1", tags=["acesso"])


def _problema(descricao: str) -> dict[str, Any]:
    return {"description": descricao, "content": {PROBLEM_JSON: {}}}


_ERROS: dict[int | str, dict[str, Any]] = {
    401: _problema("Sem access token válido"),
    403: _problema("Sem `papel:assign`, ou atribuição a si mesmo (segregação de funções)"),
}

Administrador = Annotated[UsuarioAtual, Depends(require(casos.PERMISSAO))]


class EscopoOut(BaseModel):
    tipo: str
    id: str | None


class AtribuicaoOut(BaseModel):
    id: UUID
    usuario_id: UUID
    papel: str
    escopo_tipo: str
    escopo_id: str | None
    origem: str
    valido_ate: datetime | None

    @classmethod
    def de(cls, a: casos.Atribuicao) -> Self:
        return cls(
            id=a.id,
            usuario_id=a.user_id,
            papel=a.papel,
            escopo_tipo=a.scope_type,
            escopo_id=a.scope_id,
            origem=a.origin,
            valido_ate=a.valid_until,
        )


class MeOut(BaseModel):
    """003/R5.1: para o front montar a tela inicial coerente com o perfil."""

    id: UUID
    username: str
    nome: str
    email: str | None
    origem: str
    papeis: list[AtribuicaoOut]
    permissoes: dict[str, list[EscopoOut]]


class PapelOut(BaseModel):
    codigo: str
    nome: str
    descricao: str
    escopo_exigido: str


class AtribuicaoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuario_id: UUID
    papel: str = Field(min_length=1, max_length=50)
    escopo_tipo: Literal["global", "area", "distrito", "unidade"]
    escopo_id: str | None = Field(default=None, max_length=36)
    valido_ate: datetime | None = None


@router.get("/me", summary="Perfil do usuário logado", responses={401: _ERROS[401]})
async def me(request: Request, usuario: Autenticado, sessao: SessaoDeNegocio) -> MeOut:
    """003/R5.1: só exige estar autenticado."""
    perfil = await casos.perfil(
        usuario,
        atribuicoes=request.app.state.repositorio_de_atribuicoes(sessao),
        agora=datetime.now(UTC),
    )
    return MeOut(
        id=perfil.usuario.id,
        username=perfil.usuario.username,
        nome=perfil.usuario.display_name,
        email=perfil.usuario.email,
        origem=perfil.usuario.source,
        papeis=[AtribuicaoOut.de(a) for a in perfil.atribuicoes],
        permissoes={
            codigo: [EscopoOut(tipo=str(e["tipo"]), id=e["id"]) for e in escopos]
            for codigo, escopos in perfil.permissoes.items()
        },
    )


@router.get("/admin/papeis", summary="Papéis e o escopo que cada um exige", responses=_ERROS)
async def papeis(
    request: Request, usuario: Administrador, sessao: SessaoDeNegocio
) -> list[PapelOut]:
    """003/R1, R2.1."""
    itens = await casos.listar_papeis(
        atribuicoes=request.app.state.repositorio_de_atribuicoes(sessao)
    )
    return [
        PapelOut(
            codigo=p.codigo, nome=p.nome, descricao=p.descricao, escopo_exigido=p.escopo_exigido
        )
        for p in itens
    ]


@router.get("/admin/atribuicoes", summary="Atribuições vigentes", responses=_ERROS)
async def listar(
    request: Request,
    usuario: Administrador,
    sessao: SessaoDeNegocio,
    usuario_id: Annotated[UUID | None, Query(description="Só deste usuário.")] = None,
) -> list[AtribuicaoOut]:
    itens = await casos.listar_atribuicoes(
        usuario_id,
        atribuicoes=request.app.state.repositorio_de_atribuicoes(sessao),
        agora=datetime.now(UTC),
    )
    return [AtribuicaoOut.de(a) for a in itens]


@router.post(
    "/admin/atribuicoes",
    status_code=201,
    summary="Atribuir papel",
    responses={**_ERROS, 422: _problema("Usuário, papel, escopo ou validade inválidos")},
)
async def atribuir(
    request: Request, corpo: AtribuicaoIn, usuario: Administrador, sessao: SessaoDeNegocio
) -> AtribuicaoOut:
    """003/R2.1 a R2.5: audita `papel.atribuido`; vale na próxima requisição (R4.5)."""
    estado = request.app.state
    atribuicao = await casos.atribuir(
        usuario_id=corpo.usuario_id,
        papel=corpo.papel,
        escopo_tipo=corpo.escopo_tipo,
        escopo_id=corpo.escopo_id,
        valido_ate=corpo.valido_ate,
        quem=usuario,
        ator=ator_da_requisicao(request, usuario),
        novo_id=uuid7(),
        atribuicoes=estado.repositorio_de_atribuicoes(sessao),
        permissoes=estado.repositorio_de_permissoes(sessao),
        auditoria=estado.auditoria(sessao),
    )
    return AtribuicaoOut.de(atribuicao)


@router.delete(
    "/admin/atribuicoes/{id_}",
    status_code=204,
    summary="Remover atribuição",
    responses={**_ERROS, 404: _problema("Atribuição inexistente")},
)
async def remover(
    request: Request, id_: UUID, usuario: Administrador, sessao: SessaoDeNegocio
) -> Response:
    """003/R2.4: audita `papel.removido`."""
    estado = request.app.state
    await casos.remover(
        id_,
        quem=usuario,
        ator=ator_da_requisicao(request, usuario),
        atribuicoes=estado.repositorio_de_atribuicoes(sessao),
        permissoes=estado.repositorio_de_permissoes(sessao),
        auditoria=estado.auditoria(sessao),
    )
    return Response(status_code=204)
