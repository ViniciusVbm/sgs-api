"""Rotas de equipamentos e serviços (design da 006 § Rotas; R5 e R6).

Da unidade: leitura com `unidade:read` e escrita com `equipamento:write` ou `servico:write`, no
escopo da unidade do caminho (`ResourceRef("unidade")`). Soltos: a mesma permissão de escrita,
que o caso de uso exige com escopo global (R5.2, R6.2).
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from src.core.ids import uuid7
from src.core.problem import PROBLEM_JSON
from src.modules.access.api.deps import (
    ResourceRef,
    SessaoDeNegocio,
    UsuarioAtual,
    ator_da_requisicao,
    require,
)
from src.modules.registry.api.schemas import (
    EquipamentoCreate,
    EquipamentoOut,
    EquipamentoUpdate,
    ServicoCreate,
    ServicoOut,
    ServicoUpdate,
)
from src.modules.registry.application import vinculos as casos

router = APIRouter(prefix="/api/v1", tags=["equipamentos e serviços"])

_UNIDADE = ResourceRef("unidade")


def _problema(descricao: str) -> dict[str, Any]:
    return {"description": descricao, "content": {PROBLEM_JSON: {}}}


_ERROS: dict[int | str, dict[str, Any]] = {
    401: _problema("Sem access token válido"),
    403: _problema("Sem a permissão no escopo da unidade (ou, se solto, sem escopo global)"),
    404: _problema("Unidade, equipamento ou serviço inexistente"),
    422: _problema("Campos inválidos, tipo inexistente ou equipamento de outra unidade"),
}

LeitorDaUnidade = Annotated[UsuarioAtual, Depends(require("unidade:read", _UNIDADE))]
EquipamentosDaUnidade = Annotated[
    UsuarioAtual, Depends(require(casos.PERMISSAO_EQUIPAMENTO, _UNIDADE))
]
ServicosDaUnidade = Annotated[UsuarioAtual, Depends(require(casos.PERMISSAO_SERVICO, _UNIDADE))]
EquipamentosSoltos = Annotated[UsuarioAtual, Depends(require(casos.PERMISSAO_EQUIPAMENTO))]
ServicosSoltos = Annotated[UsuarioAtual, Depends(require(casos.PERMISSAO_SERVICO))]


def _deps(request: Request, sessao: Any) -> dict[str, Any]:
    estado = request.app.state
    return {
        "vinculos": estado.repositorio_de_vinculos(sessao),
        "auditoria": estado.auditoria(sessao),
    }


# ------------------------------------------------------- equipamentos da unidade


@router.get("/unidades/{id}/equipamentos", summary="Equipamentos da unidade", responses=_ERROS)
async def listar_equipamentos_da_unidade(
    request: Request,
    id: UUID,
    usuario: LeitorDaUnidade,
    sessao: SessaoDeNegocio,
) -> list[EquipamentoOut]:
    """006/R5.1."""
    itens = await casos.listar_equipamentos(
        id, usuario=usuario, vinculos=request.app.state.repositorio_de_vinculos(sessao)
    )
    return [EquipamentoOut.de(e) for e in itens]


@router.post(
    "/unidades/{id}/equipamentos",
    status_code=201,
    summary="Adicionar equipamento à unidade",
    responses=_ERROS,
)
async def criar_equipamento_na_unidade(
    request: Request,
    response: Response,
    id: UUID,
    corpo: EquipamentoCreate,
    usuario: EquipamentosDaUnidade,
    sessao: SessaoDeNegocio,
) -> EquipamentoOut:
    """006/R5.1, R5.3: audita `unidade.equipamento_adicionado`."""
    equipamento = await casos.criar_equipamento(
        id,
        corpo.dados(),
        novo_id=uuid7(),
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    response.headers["Location"] = f"/api/v1/unidades/{id}/equipamentos/{equipamento.id}"
    return EquipamentoOut.de(equipamento)


@router.patch(
    "/unidades/{id}/equipamentos/{equipamento_id}",
    summary="Alterar equipamento da unidade",
    responses=_ERROS,
)
async def alterar_equipamento_da_unidade(
    request: Request,
    id: UUID,
    equipamento_id: UUID,
    corpo: EquipamentoUpdate,
    usuario: EquipamentosDaUnidade,
    sessao: SessaoDeNegocio,
) -> EquipamentoOut:
    equipamento = await casos.alterar_equipamento(
        id,
        equipamento_id,
        corpo.alteracoes(),
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    return EquipamentoOut.de(equipamento)


@router.delete(
    "/unidades/{id}/equipamentos/{equipamento_id}",
    status_code=204,
    summary="Remover equipamento da unidade",
    responses=_ERROS,
)
async def remover_equipamento_da_unidade(
    request: Request,
    id: UUID,
    equipamento_id: UUID,
    usuario: EquipamentosDaUnidade,
    sessao: SessaoDeNegocio,
) -> Response:
    """Os serviços ligados ficam, sem o equipamento (ON DELETE SET NULL, 011/R9.1)."""
    await casos.remover_equipamento(
        id,
        equipamento_id,
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    return Response(status_code=204)


# ------------------------------------------------------------ equipamentos soltos


@router.get("/equipamentos", summary="Equipamentos sem unidade", responses=_ERROS)
async def listar_equipamentos_soltos(
    request: Request, usuario: EquipamentosSoltos, sessao: SessaoDeNegocio
) -> list[EquipamentoOut]:
    """006/R5.2: só com `equipamento:write` global."""
    itens = await casos.listar_equipamentos(
        None, usuario=usuario, vinculos=request.app.state.repositorio_de_vinculos(sessao)
    )
    return [EquipamentoOut.de(e) for e in itens]


@router.post(
    "/equipamentos", status_code=201, summary="Cadastrar equipamento sem unidade", responses=_ERROS
)
async def criar_equipamento_solto(
    request: Request,
    response: Response,
    corpo: EquipamentoCreate,
    usuario: EquipamentosSoltos,
    sessao: SessaoDeNegocio,
) -> EquipamentoOut:
    equipamento = await casos.criar_equipamento(
        None,
        corpo.dados(),
        novo_id=uuid7(),
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    response.headers["Location"] = f"/api/v1/equipamentos/{equipamento.id}"
    return EquipamentoOut.de(equipamento)


@router.patch(
    "/equipamentos/{equipamento_id}", summary="Alterar equipamento sem unidade", responses=_ERROS
)
async def alterar_equipamento_solto(
    request: Request,
    equipamento_id: UUID,
    corpo: EquipamentoUpdate,
    usuario: EquipamentosSoltos,
    sessao: SessaoDeNegocio,
) -> EquipamentoOut:
    equipamento = await casos.alterar_equipamento(
        None,
        equipamento_id,
        corpo.alteracoes(),
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    return EquipamentoOut.de(equipamento)


@router.delete(
    "/equipamentos/{equipamento_id}",
    status_code=204,
    summary="Remover equipamento sem unidade",
    responses=_ERROS,
)
async def remover_equipamento_solto(
    request: Request,
    equipamento_id: UUID,
    usuario: EquipamentosSoltos,
    sessao: SessaoDeNegocio,
) -> Response:
    await casos.remover_equipamento(
        None,
        equipamento_id,
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    return Response(status_code=204)


# ----------------------------------------------------------- serviços da unidade


@router.get("/unidades/{id}/servicos", summary="Serviços da unidade", responses=_ERROS)
async def listar_servicos_da_unidade(
    request: Request,
    id: UUID,
    usuario: LeitorDaUnidade,
    sessao: SessaoDeNegocio,
) -> list[ServicoOut]:
    """006/R6.1, R6.3."""
    itens = await casos.listar_servicos(
        id, usuario=usuario, vinculos=request.app.state.repositorio_de_vinculos(sessao)
    )
    return [ServicoOut.de(s) for s in itens]


@router.post(
    "/unidades/{id}/servicos",
    status_code=201,
    summary="Adicionar serviço à unidade",
    responses=_ERROS,
)
async def criar_servico_na_unidade(
    request: Request,
    response: Response,
    id: UUID,
    corpo: ServicoCreate,
    usuario: ServicosDaUnidade,
    sessao: SessaoDeNegocio,
) -> ServicoOut:
    servico = await casos.criar_servico(
        id,
        corpo.dados(),
        novo_id=uuid7(),
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    response.headers["Location"] = f"/api/v1/unidades/{id}/servicos/{servico.id}"
    return ServicoOut.de(servico)


@router.patch(
    "/unidades/{id}/servicos/{servico_id}", summary="Alterar serviço da unidade", responses=_ERROS
)
async def alterar_servico_da_unidade(
    request: Request,
    id: UUID,
    servico_id: UUID,
    corpo: ServicoUpdate,
    usuario: ServicosDaUnidade,
    sessao: SessaoDeNegocio,
) -> ServicoOut:
    servico = await casos.alterar_servico(
        id,
        servico_id,
        corpo.alteracoes(),
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    return ServicoOut.de(servico)


@router.delete(
    "/unidades/{id}/servicos/{servico_id}",
    status_code=204,
    summary="Remover serviço da unidade",
    responses=_ERROS,
)
async def remover_servico_da_unidade(
    request: Request,
    id: UUID,
    servico_id: UUID,
    usuario: ServicosDaUnidade,
    sessao: SessaoDeNegocio,
) -> Response:
    await casos.remover_servico(
        id,
        servico_id,
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    return Response(status_code=204)


# ---------------------------------------------------------------- serviços soltos


@router.get("/servicos", summary="Serviços soltos (sem unidade)", responses=_ERROS)
async def listar_servicos_soltos(
    request: Request, usuario: ServicosSoltos, sessao: SessaoDeNegocio
) -> list[ServicoOut]:
    """006/R6.2: só com `servico:write` global."""
    itens = await casos.listar_servicos(
        None, usuario=usuario, vinculos=request.app.state.repositorio_de_vinculos(sessao)
    )
    return [ServicoOut.de(s) for s in itens]


@router.post("/servicos", status_code=201, summary="Cadastrar serviço solto", responses=_ERROS)
async def criar_servico_solto(
    request: Request,
    response: Response,
    corpo: ServicoCreate,
    usuario: ServicosSoltos,
    sessao: SessaoDeNegocio,
) -> ServicoOut:
    servico = await casos.criar_servico(
        None,
        corpo.dados(),
        novo_id=uuid7(),
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    response.headers["Location"] = f"/api/v1/servicos/{servico.id}"
    return ServicoOut.de(servico)


@router.patch("/servicos/{servico_id}", summary="Alterar serviço solto", responses=_ERROS)
async def alterar_servico_solto(
    request: Request,
    servico_id: UUID,
    corpo: ServicoUpdate,
    usuario: ServicosSoltos,
    sessao: SessaoDeNegocio,
) -> ServicoOut:
    servico = await casos.alterar_servico(
        None,
        servico_id,
        corpo.alteracoes(),
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    return ServicoOut.de(servico)


@router.delete(
    "/servicos/{servico_id}", status_code=204, summary="Remover serviço solto", responses=_ERROS
)
async def remover_servico_solto(
    request: Request,
    servico_id: UUID,
    usuario: ServicosSoltos,
    sessao: SessaoDeNegocio,
) -> Response:
    await casos.remover_servico(
        None,
        servico_id,
        usuario=usuario,
        ator=ator_da_requisicao(request, usuario),
        **_deps(request, sessao),
    )
    return Response(status_code=204)
