"""Casos de uso da unidade de saúde (spec 006; desativação e versão da spec 011).

Rodam na transação da requisição: o repositório e o `AuditStore` recebidos estão presos à mesma
sessão, então a unidade e o registro de auditoria são gravados juntos ou nenhum dos dois
(AGENTS.md, regra 5). Na trilha, o nome do gestor sai mascarado (decisão D2; 011/T21).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from src.core.errors import (
    Conflict,
    DomainValidationError,
    FieldError,
    NotFound,
    PreconditionFailed,
)
from src.modules.access.application.autorizacao import (
    Alvo,
    UsuarioAtual,
    escopo_de_leitura,
    exigir_escopo_amplo,
    exigir_no_escopo,
)
from src.modules.audit.application.registrar import (
    Ator,
    AuditStore,
    Entidade,
    Mudanca,
    registrar,
)
from src.modules.registry.domain.ports import (
    RepositorioDeUnidades,
    RepositorioDeVinculos,
    UnicidadeViolada,
)
from src.modules.registry.domain.unidade import (
    DadosDaUnidade,
    FiltrosDeUnidade,
    Unidade,
    campos_estruturais_alterados,
    diff,
    valor_para_auditoria,
)
from src.modules.registry.domain.vinculos import Equipamento, Servico

# Reexportados para a camada api, que só importa a application.
__all__ = [
    "DadosDaUnidade",
    "DetalheDaUnidade",
    "FiltrosDeUnidade",
    "PaginaDeUnidades",
    "Unidade",
    "atualizar_unidade",
    "criar_unidade",
    "desativar_unidade",
    "detalhar_unidade",
    "listar_unidades",
]

# `entity_type` dos eventos da unidade, também nos de equipamento e serviço (006/R5.3).
ENTIDADE = "unidade"

# Campos obrigatórios da unidade (006/R1.2): o PATCH não pode esvaziá-los.
_OBRIGATORIOS = ("name", "unit_type_id", "district_id", "cep", "address", "status")

# Campo do domínio → campo da API, para os erros apontarem o nome que o cliente enviou.
CAMPO_DA_API = {
    "name": "nome",
    "cnes": "cnes",
    "unit_type_id": "tipo_unidade_id",
    "district_id": "distrito_id",
    "cep": "cep",
    "address": "endereco",
    "neighborhood": "bairro",
    "phone": "telefone",
    "manager_name": "nome_gestor",
    "latitude": "latitude",
    "longitude": "longitude",
    "status": "status",
}


@dataclass(frozen=True, slots=True)
class PaginaDeUnidades:
    itens: tuple[Unidade, ...]
    total: int


@dataclass(frozen=True, slots=True)
class DetalheDaUnidade:
    """A unidade com os equipamentos e serviços vinculados (006/R2.5)."""

    unidade: Unidade
    equipamentos: tuple[Equipamento, ...]
    servicos: tuple[Servico, ...]


async def criar_unidade(
    dados: DadosDaUnidade,
    *,
    novo_id: UUID,
    usuario: UsuarioAtual,
    ator: Ator,
    unidades: RepositorioDeUnidades,
    auditoria: AuditStore,
) -> Unidade:
    """Cria a unidade (006/R1) e registra `unidade.criada` com todos os campos (R1.6).

    Levanta `DomainValidationError` (422) se o tipo ou o distrito não existe ou está desativado
    (R1.2), `AcessoNegado` (403) se o usuário não tem `unidade:create` no escopo da área técnica
    do tipo (R1.1), e `Conflict` (409) se o CNES já é de outra unidade (R1.3) ou se outra do
    mesmo distrito tem o mesmo nome normalizado (R1.4); os dois apontam a existente.
    """
    area = await _conferir_referencias(unidades, dados.unit_type_id, dados.district_id)
    exigir_no_escopo(
        usuario,
        "unidade:create",
        Alvo(unidade_id=novo_id, distrito_id=dados.district_id, area_id=area),
    )
    unidade = await unidades.inserir(novo_id, dados)
    if unidade is None:
        raise await _conflito(dados.cnes, dados.district_id, dados.name, unidades)
    await registrar(
        auditoria,
        acao="unidade.criada",
        ator=ator,
        entidade=Entidade(tipo=ENTIDADE, id=str(unidade.id)),
        mudancas=[
            Mudanca(campo=campo, de=None, para=valor_para_auditoria(campo, valor))
            for campo, valor in unidade.campos_de_negocio().items()
        ],
    )
    return unidade


async def listar_unidades(
    usuario: UsuarioAtual,
    filtros: FiltrosDeUnidade,
    *,
    limite: int,
    deslocamento: int,
    unidades: RepositorioDeUnidades,
) -> PaginaDeUnidades:
    """006/R2.1 a R2.4, R2.6: uma página das unidades no escopo de leitura de `unidade:read`."""
    escopo = escopo_de_leitura(usuario, "unidade:read")
    itens, total = await unidades.listar(escopo, filtros, limite, deslocamento)
    return PaginaDeUnidades(itens=tuple(itens), total=total)


async def detalhar_unidade(
    unidade_id: UUID, *, unidades: RepositorioDeUnidades, vinculos: RepositorioDeVinculos
) -> DetalheDaUnidade:
    """006/R2.5. O escopo já foi conferido pelo `require` com `ResourceRef("unidade")`."""
    unidade = await unidades.obter(unidade_id)
    if unidade is None:
        raise NotFound("Unidade não encontrada.")
    return DetalheDaUnidade(
        unidade=unidade,
        equipamentos=tuple(await vinculos.equipamentos(unidade_id)),
        servicos=tuple(await vinculos.servicos(unidade_id)),
    )


async def atualizar_unidade(
    unidade_id: UUID,
    alteracoes: Mapping[str, object],
    *,
    versao_esperada: int,
    usuario: UsuarioAtual,
    ator: Ator,
    unidades: RepositorioDeUnidades,
    auditoria: AuditStore,
) -> Unidade:
    """Aplica só os campos enviados (006/R3.1) se a versão confere (R3.2) e audita o diff (R3.5).

    - 412 se `versao_esperada` não é a atual, lida com trava;
    - 403 apontando os campos estruturais (distrito, tipo, CNES) se o escopo de `unidade:update`
      não é global nem da área (R3.4); mudar distrito ou tipo também exige o escopo no destino;
    - 422 se um obrigatório vier nulo, se o tipo ou o distrito novo não existir, ou se pedir
      `status = inativa` (a desativação é `POST /desativar`, com motivo, R4);
    - 409 se repetir o CNES ou o nome no distrito de outra unidade;
    - sem mudança nenhuma, 200 sem auditoria (R3.6).
    """
    atual = await unidades.obter(unidade_id, travar=True)
    if atual is None:
        raise NotFound("Unidade não encontrada.")
    if atual.version != versao_esperada:
        raise PreconditionFailed(
            "A unidade foi alterada depois da sua leitura. Recarregue e tente de novo.",
            extensoes={"versao_atual": str(atual.version)},
        )
    _conferir_campos(alteracoes, atual)
    mudancas = diff(atual.campos_de_negocio(), alteracoes)
    if not mudancas:
        return atual

    area_atual = await unidades.area_do_tipo(atual.unit_type_id)
    alvo_atual = Alvo(unidade_id=atual.id, distrito_id=atual.district_id, area_id=area_atual or -1)
    estruturais = campos_estruturais_alterados(mudancas)
    if estruturais:
        exigir_escopo_amplo(
            usuario,
            "unidade:update",
            alvo_atual,
            campos=tuple(CAMPO_DA_API[campo] for campo in estruturais),
        )
        novo_tipo = int(str(alteracoes.get("unit_type_id", atual.unit_type_id)))
        novo_distrito = int(str(alteracoes.get("district_id", atual.district_id)))
        if {"unit_type_id", "district_id"} & set(estruturais):
            nova_area = await _conferir_referencias(unidades, novo_tipo, novo_distrito)
            exigir_no_escopo(
                usuario,
                "unidade:update",
                Alvo(unidade_id=atual.id, distrito_id=novo_distrito, area_id=nova_area),
            )

    campos = {m.campo: m.para for m in mudancas}
    try:
        gravada = await unidades.atualizar(unidade_id, campos, versao_esperada)
    except UnicidadeViolada:
        raise await _conflito(
            str(campos.get("cnes", atual.cnes)) if campos.get("cnes", atual.cnes) else None,
            int(str(campos.get("district_id", atual.district_id))),
            str(campos.get("name", atual.name)),
            unidades,
            excluir=unidade_id,
        ) from None
    if gravada is None:  # a versão mudou entre a leitura e a escrita
        raise PreconditionFailed("A unidade foi alterada por outra pessoa. Recarregue.")
    await registrar(
        auditoria,
        acao="unidade.atualizada",
        ator=ator,
        entidade=Entidade(tipo=ENTIDADE, id=str(unidade_id)),
        mudancas=[
            Mudanca(
                campo=m.campo,
                de=valor_para_auditoria(m.campo, m.de),
                para=valor_para_auditoria(m.campo, m.para),
            )
            for m in mudancas
        ],
    )
    return gravada


async def desativar_unidade(
    unidade_id: UUID,
    *,
    motivo: str,
    ator: Ator,
    unidades: RepositorioDeUnidades,
    auditoria: AuditStore,
) -> Unidade:
    """006/R4, 011/R6 pela `sp_deactivate_unit`: 404 se não existe; já inativa, 200 sem
    auditoria (011/R6.4); senão audita `unidade.desativada` com o motivo nos metadados."""
    resultado = await unidades.desativar(unidade_id)
    if resultado is None:
        raise NotFound("Unidade não encontrada.")
    status_anterior, _ = resultado
    unidade = await unidades.obter(unidade_id)
    if unidade is None:  # pragma: no cover - a procedure acabou de travar e ler a linha
        raise NotFound("Unidade não encontrada.")
    if status_anterior != "inativa":
        await registrar(
            auditoria,
            acao="unidade.desativada",
            ator=ator,
            entidade=Entidade(tipo=ENTIDADE, id=str(unidade_id)),
            mudancas=[Mudanca(campo="status", de=status_anterior, para="inativa")],
            metadados={"motivo": motivo},
        )
    return unidade


def _conferir_campos(alteracoes: Mapping[str, object], atual: Unidade) -> None:
    erros = [
        FieldError(campo=CAMPO_DA_API[campo], mensagem="Campo obrigatório.")
        for campo in _OBRIGATORIOS
        if campo in alteracoes and alteracoes[campo] is None
    ]
    if alteracoes.get("status") == "inativa" and atual.status != "inativa":
        erros.append(
            FieldError(
                campo="status",
                mensagem="Para desativar, use POST /api/v1/unidades/{id}/desativar com o motivo.",
            )
        )
    if erros:
        raise DomainValidationError("A requisição tem campos inválidos.", errors=erros)


async def _conferir_referencias(
    unidades: RepositorioDeUnidades, unit_type_id: int, district_id: int
) -> int:
    """Área técnica do tipo; 422 se o tipo ou o distrito não existe ou está desativado."""
    area = await unidades.area_do_tipo(unit_type_id)
    erros: list[FieldError] = []
    if area is None:
        erros.append(_inexistente("tipo_unidade_id", "Tipo de unidade"))
    if not await unidades.distrito_ativo(district_id):
        erros.append(_inexistente("distrito_id", "Distrito"))
    if area is None or erros:
        raise DomainValidationError("A requisição tem campos inválidos.", errors=erros)
    return area


def _inexistente(campo: str, referencia: str) -> FieldError:
    """Erro do campo da API que aponta uma referência que não existe ou foi desativada."""
    return FieldError(campo=campo, mensagem=f"{referencia} inexistente ou desativado.")


async def _conflito(
    cnes: str | None,
    district_id: int,
    name: str,
    unidades: RepositorioDeUnidades,
    *,
    excluir: UUID | None = None,
) -> Conflict:
    """O 409 de uma unidade que o banco recusou por repetir outra, apontando a existente."""
    existente = None if cnes is None else await unidades.com_cnes(cnes)
    if existente is not None and existente != excluir:
        return Conflict(
            "Já existe uma unidade com este CNES.",
            extensoes={"unidade_existente_id": str(existente)},
        )
    existente = await unidades.com_nome(district_id, name)
    if existente is not None and existente != excluir:
        return Conflict(
            "Já existe uma unidade com este nome no distrito.",
            extensoes={"unidade_existente_id": str(existente)},
        )
    # Só sobra a chave primária, que um UUID v7 novo não repete na prática.
    return Conflict("Já existe uma unidade com estes dados.")
