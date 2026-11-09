"""Carga de demonstração (spec 010, T2): `sgs-admin seed demo`.

Lê `seeds/demo/*.json` e grava, numa transação, referências, unidades, equipamentos, serviços e
30 usuários fictícios. Passa pelos casos de uso da 006 (validação, unicidade e auditoria com o
ator sistema), como pede o design da 010. Idempotente: o que já existe pela chave natural
(código; CNES ou distrito + nome; unidade + nome; username) é pulado (R1.1). Recusa `APP_ENV=prod`
(R1.6).

A senha dos usuários de demonstração vem de `SGS_SEED_SENHA` ou é gerada e mostrada uma vez.
"""

import json
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import AppEnv, Settings
from src.core.db import create_engine
from src.core.ids import uuid7
from src.modules.access.application.autorizacao import UsuarioAtual
from src.modules.access.domain.atribuicoes import Atribuicao
from src.modules.access.domain.authorization import Global
from src.modules.access.infrastructure.repository import SqlRepositorioDeAtribuicoes
from src.modules.audit.application.registrar import Ator, Entidade, registrar
from src.modules.audit.infrastructure.repository import SqlAuditStore
from src.modules.identity.domain.users import User, UserSource
from src.modules.identity.infrastructure.passwords import Argon2PasswordHasher
from src.modules.identity.infrastructure.repository import SqlUserRepository
from src.modules.registry.application.referencias import (
    DadosDaReferencia,
    TipoDeReferencia,
    criar_referencia,
)
from src.modules.registry.application.unidades import DadosDaUnidade, criar_unidade
from src.modules.registry.application.vinculos import (
    DadosDoEquipamento,
    DadosDoServico,
    criar_equipamento,
    criar_servico,
)
from src.modules.registry.infrastructure.repository import (
    SqlRepositorioDeReferencias,
    SqlRepositorioDeUnidades,
    SqlRepositorioDeVinculos,
)

PASTA = Path(__file__).resolve().parents[2] / "seeds" / "demo"
ORIGEM = "sgs-admin seed demo"

# O seed age como o sistema, com escopo global nas permissões de escrita do cadastro.
_SISTEMA = UsuarioAtual(
    id=UUID(int=0),
    sessao_id=UUID(int=0),
    permissoes={
        "unidade:create": (Global(),),
        "equipamento:write": (Global(),),
        "servico:write": (Global(),),
    },
)


class SeedRecusado(Exception):  # noqa: N818
    """O seed não roda neste ambiente (010/R1.6)."""


@dataclass
class Contagem:
    criados: dict[str, int] = field(default_factory=dict)
    pulados: dict[str, int] = field(default_factory=dict)
    senha_gerada: str | None = field(default=None, repr=False)

    def criou(self, tipo: str) -> None:
        self.criados[tipo] = self.criados.get(tipo, 0) + 1

    def pulou(self, tipo: str) -> None:
        self.pulados[tipo] = self.pulados.get(tipo, 0) + 1


def _ler(nome: str, pasta: Path) -> dict[str, Any]:
    dados: dict[str, Any] = json.loads((pasta / nome).read_text(encoding="utf-8"))
    return dados


async def carregar(
    url: str, settings: Settings, *, senha: str | None = None, pasta: Path = PASTA
) -> Contagem:
    if settings.app_env is AppEnv.PROD:
        raise SeedRecusado("o seed de demonstração não roda em prod (010/R1.6)")
    contagem = Contagem()
    if senha is None:
        senha = contagem.senha_gerada = secrets.token_urlsafe(12)
    engine = create_engine(url, settings, pooled=False)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as sessao, sessao.begin():
            await _carregar(sessao, senha, pasta, contagem)
    finally:
        await engine.dispose()
    return contagem


async def _carregar(sessao: AsyncSession, senha: str, pasta: Path, contagem: Contagem) -> None:
    referencias = SqlRepositorioDeReferencias(sessao)
    unidades = SqlRepositorioDeUnidades(sessao)
    vinculos = SqlRepositorioDeVinculos(sessao)
    auditoria = SqlAuditStore(sessao)
    sistema = Ator()

    ids = await _ids_das_referencias(sessao)
    # Referências reais da rede usadas pelas unidades reaproveitadas da feat/003.
    dados = _ler("referencias.json", pasta)
    for item in dados["tipos_unidade"]:
        if item["codigo"] in ids["tipo_unidade"]:
            contagem.pulou("tipos_unidade")
            continue
        nova = await criar_referencia(
            TipoDeReferencia.TIPOS_UNIDADE,
            DadosDaReferencia(
                code=item["codigo"],
                name=item["nome"],
                technical_area_id=ids["area"][item["area"]],
            ),
            ator=sistema,
            referencias=referencias,
            auditoria=auditoria,
        )
        ids["tipo_unidade"][nova.code] = nova.id
        contagem.criou("tipos_unidade")
    for item in dados["tipos_equipamento"]:
        if item["codigo"] in ids["tipo_equipamento"]:
            contagem.pulou("tipos_equipamento")
            continue
        await criar_referencia(
            TipoDeReferencia.TIPOS_EQUIPAMENTO,
            DadosDaReferencia(code=item["codigo"], name=item["nome"]),
            ator=sistema,
            referencias=referencias,
            auditoria=auditoria,
        )
        ids["tipo_equipamento"][item["codigo"]] = 0
        contagem.criou("tipos_equipamento")

    # Unidades (chave natural: CNES; senão distrito + nome normalizado).
    por_nome: dict[str, UUID] = {}
    for item in _ler("unidades.json", pasta)["unidades"]:
        distrito = ids["distrito"][item["distrito"]]
        existente = None if item["cnes"] is None else await unidades.com_cnes(item["cnes"])
        if existente is None:
            existente = await unidades.com_nome(distrito, item["nome"])
        if existente:
            por_nome[item["nome"]] = existente
            contagem.pulou("unidades")
            continue
        unidade = await criar_unidade(
            DadosDaUnidade(
                name=item["nome"],
                cnes=item["cnes"],
                unit_type_id=ids["tipo_unidade"][item["tipo"]],
                district_id=distrito,
                cep=item["cep"],
                address=item["endereco"],
                neighborhood=item["bairro"],
                phone=item["telefone"],
                status=item["status"],
            ),
            novo_id=uuid7(),
            usuario=_SISTEMA,
            ator=sistema,
            unidades=unidades,
            auditoria=auditoria,
        )
        por_nome[item["nome"]] = unidade.id
        if item.get("pendencias"):
            # `pending_issues` é mantido pela validação (spec 007, ainda não implementada); o
            # seed o preenche direto para o dashboard mostrar qualidade (010/R1.3).
            await sessao.execute(
                text("UPDATE health_units SET pending_issues = :n WHERE id = :id"),
                {"n": item["pendencias"], "id": unidade.id},
            )
        contagem.criou("unidades")

    # Equipamentos e serviços (chave natural: unidade + nome).
    vinc = _ler("vinculos.json", pasta)
    equipamentos_por_nome: dict[tuple[UUID | None, str], UUID] = {}
    for item in vinc["equipamentos"]:
        unidade_id = None if item["unidade"] is None else por_nome[item["unidade"]]
        existentes = {e.name: e.id for e in await vinculos.equipamentos(unidade_id)}
        if item["nome"] in existentes:
            equipamentos_por_nome[(unidade_id, item["nome"])] = existentes[item["nome"]]
            contagem.pulou("equipamentos")
            continue
        equipamento = await criar_equipamento(
            unidade_id,
            DadosDoEquipamento(
                name=item["nome"],
                equipment_type_code=item["tipo"],
                quantity=item["quantidade"],
                status="ativo",
            ),
            novo_id=uuid7(),
            usuario=_SISTEMA,
            ator=sistema,
            vinculos=vinculos,
            auditoria=auditoria,
        )
        equipamentos_por_nome[(unidade_id, item["nome"])] = equipamento.id
        contagem.criou("equipamentos")
    for item in vinc["servicos"]:
        unidade_id = None if item["unidade"] is None else por_nome[item["unidade"]]
        if item["nome"] in {s.name for s in await vinculos.servicos(unidade_id)}:
            contagem.pulou("servicos")
            continue
        equipamento_nome = item.get("equipamento")
        await criar_servico(
            unidade_id,
            DadosDoServico(
                name=item["nome"],
                service_type_id=ids["tipo_servico"][item["tipo"]],
                in_cnes=item["no_cnes"],
                status="ativo",
                equipment_id=(
                    None
                    if equipamento_nome is None
                    else equipamentos_por_nome[(unidade_id, equipamento_nome)]
                ),
            ),
            novo_id=uuid7(),
            usuario=_SISTEMA,
            ator=sistema,
            vinculos=vinculos,
            auditoria=auditoria,
        )
        contagem.criou("servicos")

    await _usuarios(sessao, senha, pasta, ids, por_nome, contagem, auditoria, sistema)


async def _usuarios(
    sessao: AsyncSession,
    senha: str,
    pasta: Path,
    ids: Mapping[str, Mapping[str, int]],
    por_nome: Mapping[str, UUID],
    contagem: Contagem,
    auditoria: SqlAuditStore,
    sistema: Ator,
) -> None:
    """R1.4: 30 usuários fictícios, todos os papéis e escopos, com auditoria."""
    usuarios = SqlUserRepository(sessao)
    atribuicoes = SqlRepositorioDeAtribuicoes(sessao)
    hasher = Argon2PasswordHasher()
    hash_ = hasher.hash(senha)  # o mesmo hash serve a todos: são contas de demonstração
    for item in _ler("usuarios.json", pasta)["usuarios"]:
        if await usuarios.get_by_username(item["username"]) is not None:
            contagem.pulou("usuarios")
            continue
        usuario = User(
            id=uuid7(),
            username=item["username"],
            display_name=item["nome"],
            source=UserSource.LOCAL,
            password_hash=hash_,
        )
        await usuarios.add(usuario)
        escopo = item["escopo"]
        escopo_id: str | None = None
        if escopo["tipo"] == "area":
            escopo_id = str(ids["area"][escopo["valor"]])
        elif escopo["tipo"] == "distrito":
            escopo_id = str(ids["distrito"][escopo["valor"]])
        elif escopo["tipo"] == "unidade":
            escopo_id = str(por_nome[escopo["valor"]])
        await atribuicoes.inserir(
            Atribuicao(
                id=uuid7(),
                user_id=usuario.id,
                papel=item["papel"],
                scope_type=escopo["tipo"],
                scope_id=escopo_id,
                origin="direct",
                valid_until=None,
                granted_by=None,
            )
        )
        await registrar(
            auditoria,
            acao="usuario.criado",
            ator=sistema,
            entidade=Entidade(tipo="usuario", id=str(usuario.id)),
            metadados={"username": usuario.username, "papel": item["papel"], "origem": ORIGEM},
        )
        contagem.criou("usuarios")


async def _ids_das_referencias(sessao: AsyncSession) -> dict[str, dict[str, int]]:
    consultas = {
        "distrito": "SELECT code, id FROM districts",
        "area": "SELECT code, id FROM technical_areas",
        "tipo_unidade": "SELECT code, id FROM unit_types",
        "tipo_equipamento": "SELECT code, id FROM equipment_types",
        "tipo_servico": "SELECT code, id FROM service_types",
    }
    return {
        chave: {codigo: int(id_) for codigo, id_ in (await sessao.execute(text(sql))).all()}
        for chave, sql in consultas.items()
    }
