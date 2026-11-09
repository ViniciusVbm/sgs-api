"""Rotas das tabelas de referência (design da 006 § Rotas; R7; correção de código da 011/T18).

Leitura com `unidade:read`, que todo perfil de negócio tem (o design diz "autenticado"; a regra
4 do AGENTS.md pede uma permissão declarada). Escrita só com `regra_validacao:manage`, do Gestor
de Dados (R7.2).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request, Response

from src.core.problem import PROBLEM_JSON
from src.modules.access.api.deps import (
    SessaoDeNegocio,
    UsuarioAtual,
    ator_da_requisicao,
    require,
)
from src.modules.registry.api.schemas import ReferenciaCreate, ReferenciaOut, ReferenciaUpdate
from src.modules.registry.application.referencias import (
    TipoDeReferencia,
    alterar_referencia,
    criar_referencia,
    listar_referencias,
)

router = APIRouter(prefix="/api/v1/referencias", tags=["referências"])

_ERROS: dict[int | str, dict[str, Any]] = {
    401: {"description": "Sem access token válido", "content": {PROBLEM_JSON: {}}},
    403: {"description": "Sem a permissão", "content": {PROBLEM_JSON: {}}},
}

Leitor = Annotated[UsuarioAtual, Depends(require("unidade:read"))]
Gestor = Annotated[UsuarioAtual, Depends(require("regra_validacao:manage"))]


@router.get("/{tipo}", summary="Listar uma tabela de referência", responses=_ERROS)
async def listar(
    request: Request, tipo: TipoDeReferencia, usuario: Leitor, sessao: SessaoDeNegocio
) -> list[ReferenciaOut]:
    """006/R7.1: distritos, áreas técnicas e tipos de unidade, de equipamento e de serviço."""
    itens = await listar_referencias(
        tipo, referencias=request.app.state.repositorio_de_referencias(sessao)
    )
    return [ReferenciaOut.de(item) for item in itens]


@router.post(
    "/{tipo}",
    status_code=201,
    summary="Incluir item de referência",
    responses={
        **_ERROS,
        409: {"description": "Código repetido", "content": {PROBLEM_JSON: {}}},
        422: {"description": "Campos inválidos", "content": {PROBLEM_JSON: {}}},
    },
)
async def criar(
    request: Request,
    tipo: TipoDeReferencia,
    corpo: ReferenciaCreate,
    usuario: Gestor,
    sessao: SessaoDeNegocio,
) -> ReferenciaOut:
    """006/R7.2."""
    estado = request.app.state
    item = await criar_referencia(
        tipo,
        corpo.dados(),
        ator=ator_da_requisicao(request, usuario),
        referencias=estado.repositorio_de_referencias(sessao),
        auditoria=estado.auditoria(sessao),
    )
    return ReferenciaOut.de(item)


@router.patch(
    "/{tipo}/{id_}",
    summary="Alterar item de referência (código, nome, ativo)",
    responses={
        **_ERROS,
        404: {"description": "Item inexistente", "content": {PROBLEM_JSON: {}}},
        409: {"description": "Código repetido", "content": {PROBLEM_JSON: {}}},
    },
)
async def alterar(
    request: Request,
    response: Response,
    tipo: TipoDeReferencia,
    id_: Annotated[int, Path(ge=1, le=32767)],
    corpo: ReferenciaUpdate,
    usuario: Gestor,
    sessao: SessaoDeNegocio,
) -> ReferenciaOut:
    """006/R7.2, R7.3; 011/R9.2: o código novo de um tipo de equipamento chega aos equipamentos
    pela cascata, e `referencia.atualizada` registra `equipamentos_afetados`."""
    estado = request.app.state
    item = await alterar_referencia(
        tipo,
        id_,
        corpo.alteracoes(),
        ator=ator_da_requisicao(request, usuario),
        referencias=estado.repositorio_de_referencias(sessao),
        auditoria=estado.auditoria(sessao),
    )
    return ReferenciaOut.de(item)
