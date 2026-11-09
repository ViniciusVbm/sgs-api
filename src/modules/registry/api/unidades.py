"""Rotas da unidade de saúde (design da 006 § Rotas; desativação da 011/T16)."""

import re
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from src.core.errors import PreconditionFailed, PreconditionRequired
from src.core.ids import uuid7
from src.core.paginacao import TAMANHO_PADRAO, NumeroDaPagina, PaginaOut, TamanhoDaPagina
from src.core.problem import PROBLEM_JSON
from src.modules.access.api.deps import (
    ResourceRef,
    SessaoDeNegocio,
    UsuarioAtual,
    ator_da_requisicao,
    require,
)
from src.modules.registry.api.schemas import (
    DesativacaoIn,
    StatusDaUnidade,
    UnidadeCreate,
    UnidadeDetalheOut,
    UnidadeOut,
    UnidadeUpdate,
)
from src.modules.registry.application.unidades import (
    FiltrosDeUnidade,
    atualizar_unidade,
    criar_unidade,
    desativar_unidade,
    detalhar_unidade,
    listar_unidades,
)

router = APIRouter(prefix="/api/v1", tags=["unidades"])

_UNIDADE = ResourceRef("unidade")
_ID_DE_REFERENCIA_MAXIMO = 32767
_ETAG = re.compile(r'^(?:W/)?"([0-9]{1,9})"$')


def _problema(descricao: str) -> dict[str, Any]:
    """Resposta de erro em problem+json (spec 001), para o contrato."""
    return {"description": descricao, "content": {PROBLEM_JSON: {}}}


_ERROS_COMUNS: dict[int | str, dict[str, Any]] = {
    401: _problema("Sem access token válido"),
    403: _problema("Sem a permissão no escopo da unidade"),
    404: _problema("Unidade inexistente"),
}


def _versao_do_if_match(if_match: str | None) -> int:
    """006/R3.2: 428 sem `If-Match`; 412 se ele não for um ETag desta API."""
    if if_match is None:
        raise PreconditionRequired("Envie o cabeçalho If-Match com o ETag da unidade.")
    casamento = _ETAG.fullmatch(if_match.strip())
    if casamento is None:
        raise PreconditionFailed("If-Match não corresponde a uma versão desta unidade.")
    return int(casamento.group(1))


@router.get("/unidades", summary="Listar e buscar unidades", responses=_ERROS_COMUNS)
async def listar(
    request: Request,
    usuario: Annotated[UsuarioAtual, Depends(require("unidade:read"))],
    sessao: SessaoDeNegocio,
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=100, description="Texto em nome ou CNES (sem acento)."),
    ] = None,
    tipo: Annotated[int | None, Query(ge=1, le=_ID_DE_REFERENCIA_MAXIMO)] = None,
    area: Annotated[int | None, Query(ge=1, le=_ID_DE_REFERENCIA_MAXIMO)] = None,
    distrito: Annotated[int | None, Query(ge=1, le=_ID_DE_REFERENCIA_MAXIMO)] = None,
    status: StatusDaUnidade | None = None,
    com_pendencias: bool | None = None,
    ordem: Literal["nome", "distrito", "atualizacao"] = "nome",
    pagina: NumeroDaPagina = 1,
    tamanho: TamanhoDaPagina = TAMANHO_PADRAO,
) -> PaginaOut[UnidadeOut]:
    """006/R2.1 a R2.4, R2.6: paginada (padrão 20, máximo 100), no escopo de leitura."""
    resultado = await listar_unidades(
        usuario,
        FiltrosDeUnidade(
            q=q,
            tipo=tipo,
            area=area,
            distrito=distrito,
            status=status,
            com_pendencias=com_pendencias,
            ordem=ordem,
        ),
        limite=tamanho,
        deslocamento=(pagina - 1) * tamanho,
        unidades=request.app.state.repositorio_de_unidades(sessao),
    )
    return PaginaOut(
        itens=[UnidadeOut.de(u) for u in resultado.itens],
        total=resultado.total,
        pagina=pagina,
        tamanho=tamanho,
    )


@router.post(
    "/unidades",
    status_code=201,
    summary="Cadastrar unidade de saúde",
    responses={
        401: _problema("Sem access token válido"),
        403: _problema("Sem `unidade:create` na área técnica do tipo informado"),
        409: _problema("Já existe unidade com o mesmo CNES ou o mesmo nome no distrito"),
        422: _problema("Campos inválidos, ou tipo de unidade ou distrito inexistente"),
    },
)
async def criar(
    request: Request,
    response: Response,
    corpo: UnidadeCreate,
    usuario: Annotated[UsuarioAtual, Depends(require("unidade:create"))],
    sessao: SessaoDeNegocio,
) -> UnidadeOut:
    """006/R1. Responde com a unidade criada, o `Location` dela e o `ETag` da versão."""
    estado = request.app.state
    unidade = await criar_unidade(
        corpo.dados(),
        novo_id=uuid7(),
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        unidades=estado.repositorio_de_unidades(sessao),
        auditoria=estado.auditoria(sessao),
    )
    response.headers["Location"] = f"/api/v1/unidades/{unidade.id}"
    response.headers["ETag"] = f'"{unidade.version}"'
    return UnidadeOut.de(unidade)


@router.get(
    "/unidades/{id}",
    summary="Detalhar unidade com equipamentos e serviços",
    responses=_ERROS_COMUNS,
)
async def detalhar(
    request: Request,
    response: Response,
    id: UUID,
    usuario: Annotated[UsuarioAtual, Depends(require("unidade:read", _UNIDADE))],
    sessao: SessaoDeNegocio,
) -> UnidadeDetalheOut:
    """006/R2.5, R2.6. O `ETag` é a versão que o `If-Match` do PATCH deve enviar."""
    estado = request.app.state
    detalhe = await detalhar_unidade(
        id,
        unidades=estado.repositorio_de_unidades(sessao),
        vinculos=estado.repositorio_de_vinculos(sessao),
    )
    response.headers["ETag"] = f'"{detalhe.unidade.version}"'
    return UnidadeDetalheOut.do_detalhe(detalhe)


@router.patch(
    "/unidades/{id}",
    summary="Atualizar unidade (If-Match)",
    responses={
        **_ERROS_COMUNS,
        409: _problema("Repete o CNES ou o nome no distrito de outra unidade"),
        412: _problema("A versão do If-Match não é a atual"),
        422: _problema("Campos inválidos"),
        428: _problema("Falta o If-Match"),
    },
)
async def atualizar(
    request: Request,
    response: Response,
    id: UUID,
    corpo: UnidadeUpdate,
    usuario: Annotated[UsuarioAtual, Depends(require("unidade:update", _UNIDADE))],
    sessao: SessaoDeNegocio,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> UnidadeOut:
    """006/R3. Só os campos enviados mudam; a resposta traz o `ETag` novo."""
    estado = request.app.state
    unidade = await atualizar_unidade(
        id,
        corpo.alteracoes(),
        versao_esperada=_versao_do_if_match(if_match),
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        unidades=estado.repositorio_de_unidades(sessao),
        auditoria=estado.auditoria(sessao),
    )
    response.headers["ETag"] = f'"{unidade.version}"'
    return UnidadeOut.de(unidade)


@router.post(
    "/unidades/{id}/desativar",
    summary="Desativar unidade (procedimento sp_deactivate_unit)",
    responses={**_ERROS_COMUNS, 422: _problema("Motivo ausente ou curto")},
)
async def desativar(
    request: Request,
    response: Response,
    id: UUID,
    corpo: DesativacaoIn,
    usuario: Annotated[UsuarioAtual, Depends(require("unidade:deactivate", _UNIDADE))],
    sessao: SessaoDeNegocio,
) -> UnidadeOut:
    """006/R4, 011/R6.2 a R6.4: muda para `inativa` e audita; já inativa responde 200 sem
    auditoria. Nunca apaga (R4.2)."""
    estado = request.app.state
    unidade = await desativar_unidade(
        id,
        motivo=corpo.motivo,
        ator=ator_da_requisicao(request, usuario),
        unidades=estado.repositorio_de_unidades(sessao),
        auditoria=estado.auditoria(sessao),
    )
    response.headers["ETag"] = f'"{unidade.version}"'
    return UnidadeOut.de(unidade)
