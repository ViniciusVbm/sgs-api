"""Casos de uso de equipamentos e serviços (spec 006, R5 e R6).

Vinculados a uma unidade, o escopo já foi conferido pelo `require(..., ResourceRef("unidade"))`
da rota, e toda mudança é auditada no nível da unidade (`entity_type = 'unidade'`, R5.3), para
aparecer no histórico dela (`vw_unit_history`, 011/R4.4). Soltos (sem unidade) só com escopo
global (R5.2, R6.2), auditados com a própria entidade.
"""

from collections.abc import Mapping
from uuid import UUID

from src.core.errors import DomainValidationError, FieldError, NotFound
from src.modules.access.application.autorizacao import UsuarioAtual, exigir_escopo_global
from src.modules.audit.application.registrar import (
    Ator,
    AuditStore,
    Entidade,
    Mudanca,
    registrar,
)
from src.modules.registry.domain.ports import RepositorioDeVinculos
from src.modules.registry.domain.unidade import diff, valor_para_auditoria
from src.modules.registry.domain.vinculos import (
    DadosDoEquipamento,
    DadosDoServico,
    Equipamento,
    Servico,
)

__all__ = [
    "DadosDoEquipamento",
    "DadosDoServico",
    "Equipamento",
    "Servico",
    "alterar_equipamento",
    "alterar_servico",
    "criar_equipamento",
    "criar_servico",
    "listar_equipamentos",
    "listar_servicos",
    "remover_equipamento",
    "remover_servico",
]

PERMISSAO_EQUIPAMENTO = "equipamento:write"
PERMISSAO_SERVICO = "servico:write"


# ---------------------------------------------------------------- equipamentos


async def listar_equipamentos(
    unidade_id: UUID | None, *, usuario: UsuarioAtual, vinculos: RepositorioDeVinculos
) -> list[Equipamento]:
    """Os da unidade (escopo pela rota) ou, sem unidade, os soltos (só escopo global)."""
    if unidade_id is None:
        exigir_escopo_global(usuario, PERMISSAO_EQUIPAMENTO)
    return await vinculos.equipamentos(unidade_id)


async def criar_equipamento(
    unidade_id: UUID | None,
    dados: DadosDoEquipamento,
    *,
    novo_id: UUID,
    usuario: UsuarioAtual,
    ator: Ator,
    vinculos: RepositorioDeVinculos,
    auditoria: AuditStore,
) -> Equipamento:
    """006/R5.1, R5.2: 422 se o tipo não existe ou está desativado."""
    if unidade_id is None:
        exigir_escopo_global(usuario, PERMISSAO_EQUIPAMENTO)
    await _conferir_tipo_de_equipamento(vinculos, dados.equipment_type_code)
    equipamento = await vinculos.inserir_equipamento(novo_id, unidade_id, dados)
    await _auditar(
        auditoria,
        ator,
        unidade_id,
        "equipamento",
        equipamento.id,
        "adicionado",
        [
            Mudanca(campo=c, de=None, para=valor_para_auditoria(c, v))
            for c, v in equipamento.campos_de_negocio().items()
        ],
    )
    return equipamento


async def alterar_equipamento(
    unidade_id: UUID | None,
    equipamento_id: UUID,
    alteracoes: Mapping[str, object],
    *,
    usuario: UsuarioAtual,
    ator: Ator,
    vinculos: RepositorioDeVinculos,
    auditoria: AuditStore,
) -> Equipamento:
    """Só os campos enviados; 404 se o equipamento não é da unidade da rota; sem mudança, sem
    auditoria."""
    if unidade_id is None:
        exigir_escopo_global(usuario, PERMISSAO_EQUIPAMENTO)
    atual = await _equipamento_da_rota(vinculos, unidade_id, equipamento_id)
    _sem_nulos(alteracoes, ("name", "equipment_type_code", "quantity", "status"))
    if "equipment_type_code" in alteracoes:
        await _conferir_tipo_de_equipamento(vinculos, str(alteracoes["equipment_type_code"]))
    mudancas = diff(atual.campos_de_negocio(), alteracoes)
    if not mudancas:
        return atual
    gravado = await vinculos.atualizar_equipamento(
        equipamento_id, {m.campo: m.para for m in mudancas}
    )
    if gravado is None:  # pragma: no cover - lido acima na mesma transação
        raise NotFound("Equipamento não encontrado.")
    await _auditar(
        auditoria,
        ator,
        unidade_id,
        "equipamento",
        equipamento_id,
        "alterado",
        [
            Mudanca(
                campo=m.campo,
                de=valor_para_auditoria(m.campo, m.de),
                para=valor_para_auditoria(m.campo, m.para),
            )
            for m in mudancas
        ],
    )
    return gravado


async def remover_equipamento(
    unidade_id: UUID | None,
    equipamento_id: UUID,
    *,
    usuario: UsuarioAtual,
    ator: Ator,
    vinculos: RepositorioDeVinculos,
    auditoria: AuditStore,
) -> None:
    """Exclusão física (decisão U5 da 011); os serviços ficam, sem o equipamento (SET NULL)."""
    if unidade_id is None:
        exigir_escopo_global(usuario, PERMISSAO_EQUIPAMENTO)
    atual = await _equipamento_da_rota(vinculos, unidade_id, equipamento_id)
    desligados = await vinculos.remover_equipamento(equipamento_id)
    await _auditar(
        auditoria,
        ator,
        unidade_id,
        "equipamento",
        equipamento_id,
        "removido",
        [
            Mudanca(campo=c, de=valor_para_auditoria(c, v), para=None)
            for c, v in atual.campos_de_negocio().items()
        ],
        extras={"servicos_desvinculados": desligados},
    )


# -------------------------------------------------------------------- serviços


async def listar_servicos(
    unidade_id: UUID | None, *, usuario: UsuarioAtual, vinculos: RepositorioDeVinculos
) -> list[Servico]:
    if unidade_id is None:
        exigir_escopo_global(usuario, PERMISSAO_SERVICO)
    return await vinculos.servicos(unidade_id)


async def criar_servico(
    unidade_id: UUID | None,
    dados: DadosDoServico,
    *,
    novo_id: UUID,
    usuario: UsuarioAtual,
    ator: Ator,
    vinculos: RepositorioDeVinculos,
    auditoria: AuditStore,
) -> Servico:
    """006/R6.1 a R6.3: 422 se o tipo não existe ou se o equipamento não é da mesma unidade."""
    if unidade_id is None:
        exigir_escopo_global(usuario, PERMISSAO_SERVICO)
    await _conferir_servico(vinculos, unidade_id, dados.service_type_id, dados.equipment_id)
    servico = await vinculos.inserir_servico(novo_id, unidade_id, dados)
    await _auditar(
        auditoria,
        ator,
        unidade_id,
        "servico",
        servico.id,
        "adicionado",
        [Mudanca(campo=c, de=None, para=_json(v)) for c, v in servico.campos_de_negocio().items()],
    )
    return servico


async def alterar_servico(
    unidade_id: UUID | None,
    servico_id: UUID,
    alteracoes: Mapping[str, object],
    *,
    usuario: UsuarioAtual,
    ator: Ator,
    vinculos: RepositorioDeVinculos,
    auditoria: AuditStore,
) -> Servico:
    if unidade_id is None:
        exigir_escopo_global(usuario, PERMISSAO_SERVICO)
    atual = await _servico_da_rota(vinculos, unidade_id, servico_id)
    _sem_nulos(alteracoes, ("name", "service_type_id", "in_cnes", "status"))
    tipo = int(str(alteracoes.get("service_type_id", atual.service_type_id)))
    equipamento = alteracoes.get("equipment_id", atual.equipment_id)
    await _conferir_servico(
        vinculos, unidade_id, tipo, None if equipamento is None else UUID(str(equipamento))
    )
    mudancas = diff(atual.campos_de_negocio(), alteracoes)
    if not mudancas:
        return atual
    gravado = await vinculos.atualizar_servico(servico_id, {m.campo: m.para for m in mudancas})
    if gravado is None:  # pragma: no cover - lido acima na mesma transação
        raise NotFound("Serviço não encontrado.")
    await _auditar(
        auditoria,
        ator,
        unidade_id,
        "servico",
        servico_id,
        "alterado",
        [Mudanca(campo=m.campo, de=_json(m.de), para=_json(m.para)) for m in mudancas],
    )
    return gravado


async def remover_servico(
    unidade_id: UUID | None,
    servico_id: UUID,
    *,
    usuario: UsuarioAtual,
    ator: Ator,
    vinculos: RepositorioDeVinculos,
    auditoria: AuditStore,
) -> None:
    if unidade_id is None:
        exigir_escopo_global(usuario, PERMISSAO_SERVICO)
    atual = await _servico_da_rota(vinculos, unidade_id, servico_id)
    await vinculos.remover_servico(servico_id)
    await _auditar(
        auditoria,
        ator,
        unidade_id,
        "servico",
        servico_id,
        "removido",
        [Mudanca(campo=c, de=_json(v), para=None) for c, v in atual.campos_de_negocio().items()],
    )


# ------------------------------------------------------------------- auxiliares


async def _equipamento_da_rota(
    vinculos: RepositorioDeVinculos, unidade_id: UUID | None, equipamento_id: UUID
) -> Equipamento:
    equipamento = await vinculos.obter_equipamento(equipamento_id)
    if equipamento is None or equipamento.unit_id != unidade_id:
        raise NotFound("Equipamento não encontrado.")
    return equipamento


async def _servico_da_rota(
    vinculos: RepositorioDeVinculos, unidade_id: UUID | None, servico_id: UUID
) -> Servico:
    servico = await vinculos.obter_servico(servico_id)
    if servico is None or servico.unit_id != unidade_id:
        raise NotFound("Serviço não encontrado.")
    return servico


async def _conferir_tipo_de_equipamento(vinculos: RepositorioDeVinculos, codigo: str) -> None:
    if not await vinculos.tipo_de_equipamento_ativo(codigo):
        raise DomainValidationError(
            "A requisição tem campos inválidos.",
            errors=[FieldError(campo="tipo_codigo", mensagem="Tipo de equipamento inexistente.")],
        )


async def _conferir_servico(
    vinculos: RepositorioDeVinculos,
    unidade_id: UUID | None,
    service_type_id: int,
    equipment_id: UUID | None,
) -> None:
    erros: list[FieldError] = []
    if not await vinculos.tipo_de_servico_ativo(service_type_id):
        erros.append(FieldError(campo="tipo_servico_id", mensagem="Tipo de serviço inexistente."))
    if equipment_id is not None:
        equipamento = await vinculos.obter_equipamento(equipment_id)
        if equipamento is None or equipamento.unit_id != unidade_id:
            erros.append(
                FieldError(
                    campo="equipamento_id",
                    mensagem="Equipamento inexistente ou de outra unidade.",
                )
            )
    if erros:
        raise DomainValidationError("A requisição tem campos inválidos.", errors=erros)


def _sem_nulos(alteracoes: Mapping[str, object], obrigatorios: tuple[str, ...]) -> None:
    nulos = [campo for campo in obrigatorios if campo in alteracoes and alteracoes[campo] is None]
    if nulos:
        raise DomainValidationError(
            "A requisição tem campos inválidos.",
            errors=[FieldError(campo=campo, mensagem="Campo obrigatório.") for campo in nulos],
        )


def _json(valor: object) -> object:
    """UUID vira texto na trilha (JSON)."""
    return str(valor) if isinstance(valor, UUID) else valor


async def _auditar(
    auditoria: AuditStore,
    ator: Ator,
    unidade_id: UUID | None,
    tipo: str,
    id_: UUID,
    verbo: str,
    mudancas: list[Mudanca],
    *,
    extras: Mapping[str, object] | None = None,
) -> None:
    """Na unidade: `unidade.<tipo>_<verbo>` com o id do vínculo nos metadados (006/R5.3).
    Solto: `<tipo>.<verbo>` na própria entidade."""
    metadados: dict[str, object] = {f"{tipo}_id": str(id_), **(extras or {})}
    if unidade_id is not None:
        acao, entidade = f"unidade.{tipo}_{verbo}", Entidade(tipo="unidade", id=str(unidade_id))
    else:
        acao, entidade = f"{tipo}.{verbo}", Entidade(tipo=tipo, id=str(id_))
    await registrar(
        auditoria, acao=acao, ator=ator, entidade=entidade, mudancas=mudancas, metadados=metadados
    )
