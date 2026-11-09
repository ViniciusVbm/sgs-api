"""Casos de uso das tabelas de referência (spec 006, R7; correção de código da 011/R9.2).

A permissão (`regra_validacao:manage`, só do Gestor de Dados) é conferida pela rota. Toda
inclusão e alteração é auditada como `referencia.criada` e `referencia.atualizada`, com a
entidade `referencia` e o id `<tipo>:<id>`.
"""

from collections.abc import Mapping

from src.core.errors import Conflict, DomainValidationError, FieldError, NotFound
from src.modules.audit.application.registrar import (
    Ator,
    AuditStore,
    Entidade,
    Mudanca,
    registrar,
)
from src.modules.registry.domain.ports import RepositorioDeReferencias, UnicidadeViolada
from src.modules.registry.domain.referencias import DadosDaReferencia, Referencia, TipoDeReferencia
from src.modules.registry.domain.unidade import diff

__all__ = [
    "DadosDaReferencia",
    "Referencia",
    "TipoDeReferencia",
    "alterar_referencia",
    "criar_referencia",
    "listar_referencias",
]


async def listar_referencias(
    tipo: TipoDeReferencia, *, referencias: RepositorioDeReferencias
) -> list[Referencia]:
    """006/R7.1: todos os itens, ativos e desativados (o formulário mostra só os ativos)."""
    return await referencias.listar(tipo)


async def criar_referencia(
    tipo: TipoDeReferencia,
    dados: DadosDaReferencia,
    *,
    ator: Ator,
    referencias: RepositorioDeReferencias,
    auditoria: AuditStore,
) -> Referencia:
    """006/R7.2: 409 se o código já existe; 422 se faltar a área do tipo de unidade."""
    if tipo.tem_area:
        await _conferir_area(referencias, dados.technical_area_id)
    try:
        nova = await referencias.inserir(tipo, dados)
    except UnicidadeViolada:
        raise Conflict("Já existe um item com este código.") from None
    await registrar(
        auditoria,
        acao="referencia.criada",
        ator=ator,
        entidade=Entidade(tipo="referencia", id=f"{tipo.value}:{nova.id}"),
        mudancas=[
            Mudanca(campo=c, de=None, para=v)
            for c, v in _campos(nova).items()
            if v is not None or c != "technical_area_id"
        ],
    )
    return nova


async def alterar_referencia(
    tipo: TipoDeReferencia,
    id_: int,
    alteracoes: Mapping[str, object],
    *,
    ator: Ator,
    referencias: RepositorioDeReferencias,
    auditoria: AuditStore,
) -> Referencia:
    """006/R7.2, R7.3: corrigir o código de um tipo de equipamento chega a todos os equipamentos
    pela cascata da FK, e a auditoria registra `equipamentos_afetados` (011/R9.2)."""
    atual = await referencias.obter(tipo, id_)
    if atual is None:
        raise NotFound("Item de referência não encontrado.")
    if "technical_area_id" in alteracoes:
        if not tipo.tem_area:
            raise DomainValidationError(
                "A requisição tem campos inválidos.",
                errors=[FieldError(campo="area_tecnica_id", mensagem="Só tipos de unidade.")],
            )
        await _conferir_area(referencias, alteracoes["technical_area_id"])
    mudancas = diff(_campos(atual), alteracoes)
    if not mudancas:
        return atual
    metadados: dict[str, object] = {}
    codigo_mudou = any(m.campo == "code" for m in mudancas)
    if tipo is TipoDeReferencia.TIPOS_EQUIPAMENTO and codigo_mudou:
        metadados["equipamentos_afetados"] = await referencias.equipamentos_com_codigo(atual.code)
    try:
        gravada = await referencias.atualizar(tipo, id_, {m.campo: m.para for m in mudancas})
    except UnicidadeViolada:
        raise Conflict("Já existe um item com este código.") from None
    await registrar(
        auditoria,
        acao="referencia.atualizada",
        ator=ator,
        entidade=Entidade(tipo="referencia", id=f"{tipo.value}:{id_}"),
        mudancas=[Mudanca(campo=m.campo, de=m.de, para=m.para) for m in mudancas],
        metadados=metadados or None,
    )
    return gravada


def _campos(referencia: Referencia) -> dict[str, object]:
    return {
        "code": referencia.code,
        "name": referencia.name,
        "is_active": referencia.is_active,
        "technical_area_id": referencia.technical_area_id,
    }


async def _conferir_area(referencias: RepositorioDeReferencias, area: object) -> None:
    if area is None or not await referencias.area_existe(int(str(area))):
        raise DomainValidationError(
            "A requisição tem campos inválidos.",
            errors=[FieldError(campo="area_tecnica_id", mensagem="Área técnica inexistente.")],
        )
