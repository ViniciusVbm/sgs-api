"""Tipo de ator e origem de cada evento da trilha (spec 013, T2; R1.1 a R1.4)."""

from typing import Any
from uuid import UUID

import httpx
from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy import text

from src.core.ids import uuid7
from src.tools.seed_demo import ORIGEM as ORIGEM_DO_SEED
from src.tools.seed_demo import carregar
from src.tools.sgs_admin import criar_usuario
from tests.factories import make_settings
from tests.integration.acesso import GLOBAL, Sessoes, bearer, id_pelo_codigo, logado
from tests.integration.identity.autenticacao import cadastrar_e_entrar, login, usuario_local
from tests.integration.postgres import BancoDeTeste, motor

_COLUNAS = (
    "action, actor_type, origin, actor_user_id, actor_roles, entity_type, entity_id, ip,"
    " user_agent, metadata"
)


async def _trilha(sessoes: Sessoes, acao: str | None = None) -> list[dict[str, Any]]:
    async with sessoes() as sessao:
        resultado = await sessao.execute(
            text(
                f"SELECT {_COLUNAS} FROM audit_log"  # noqa: S608 - colunas fixas
                " WHERE CAST(:acao AS text) IS NULL OR action = :acao ORDER BY id"
            ),
            {"acao": acao},
        )
        return [dict(linha) for linha in resultado.mappings()]


async def _trilha_do_banco(url: str) -> list[dict[str, Any]]:
    engine = motor(url)
    async with engine.connect() as conexao:
        resultado = await conexao.execute(
            text(f"SELECT {_COLUNAS} FROM audit_log ORDER BY id")  # noqa: S608 - colunas fixas
        )
        linhas = [dict(linha) for linha in resultado.mappings()]
    await engine.dispose()
    return linhas


async def test_evento_da_api_e_de_usuario(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R1.1, R1.2: a escrita pela API é do usuário autenticado, com origem `api`. Cabeçalhos
    enviados pelo cliente não mudam o tipo nem a origem."""
    gestor = await logado(sessoes, ("GESTOR_DADOS", GLOBAL))
    corpo = {
        "nome": "CAPS Espaço Azul",
        "tipo_unidade_id": await id_pelo_codigo(sessoes, "tipo_unidade", "CAPS_II"),
        "distrito_id": await id_pelo_codigo(sessoes, "distrito", "DS-I"),
        "cep": "50010100",
        "endereco": "Rua do Sol, 150",
        "status": "ativa",
    }
    forjados = {"X-Actor-Type": "sistema", "X-Origin": "sgs-admin seed demo", "X-User-Id": "0"}

    resposta = await cliente.post(
        "/api/v1/unidades", json=corpo, headers=bearer(app, gestor) | forjados
    )

    assert resposta.status_code == 201, resposta.text
    [evento] = await _trilha(sessoes, "unidade.criada")
    assert (evento["actor_type"], evento["origin"]) == ("usuario", "api")
    assert evento["actor_user_id"] == gestor.user_id
    assert evento["actor_roles"] == ["GESTOR_DADOS"]


async def test_seed_tem_tipo_seed_sem_usuario(banco: BancoDeTeste) -> None:
    """013/R1.1, R1.2: o seed não é uma pessoa; nenhum evento dele tem usuário."""
    await carregar(
        banco.url_api, make_settings(database_url=SecretStr(banco.url_api)), senha="x" * 12
    )

    trilha = await _trilha_do_banco(banco.url_api)

    assert trilha
    assert {(e["actor_type"], e["origin"]) for e in trilha} == {("seed", ORIGEM_DO_SEED)}
    assert all(e["actor_user_id"] is None for e in trilha)
    # 013/T3: evento fora de HTTP não ganha IP nem User-Agent artificiais.
    assert all(e["ip"] is None and e["user_agent"] is None for e in trilha)


async def test_create_user_tem_tipo_cli_admin(banco: BancoDeTeste) -> None:
    """013/R1.1, R1.2: o `sgs-admin create-user` é comando administrativo, sem usuário no ator;
    o usuário criado fica na entidade."""
    usuario_id = await criar_usuario(
        banco.url_api,
        make_settings(database_url=SecretStr(banco.url_api)),
        username="admin",
        nome="Administrador",
        email=None,
        senha="senha-do-admin-123",
        papel="ADMIN_TI",
    )

    trilha = await _trilha_do_banco(banco.url_api)

    assert [e["action"] for e in trilha] == ["usuario.criado", "papel.atribuido"]
    for evento in trilha:
        assert (evento["actor_type"], evento["origin"]) == ("cli_admin", "sgs-admin create-user")
        assert evento["actor_user_id"] is None
        assert (evento["entity_type"], evento["entity_id"]) == ("usuario", usuario_id)
        assert (evento["ip"], evento["user_agent"]) == (None, None)


async def test_login_de_inexistente_e_anonimo(cliente: httpx.AsyncClient, sessoes: Sessoes) -> None:
    """013/R1.3: sem conta identificada, o ator é `anonimo`, sem usuário e sem entidade."""
    resposta = await login(cliente, "ninguem", "qualquer")

    assert resposta.status_code == 401
    [evento] = await _trilha(sessoes, "auth.login_failed")
    assert (evento["actor_type"], evento["origin"]) == ("anonimo", "api")
    assert evento["actor_user_id"] is None
    assert evento["entity_type"] is None


async def test_bloqueio_e_do_sistema(cliente: httpx.AsyncClient, sessoes: Sessoes) -> None:
    """013/R1.3: o bloqueio automático é ato do `sistema`, com a conta afetada na entidade; as
    tentativas com senha errada continuam atribuídas à conta."""
    joao = await usuario_local(sessoes, "joao")
    for _ in range(5):
        await login(cliente, "joao", "senha-errada")

    [bloqueio] = await _trilha(sessoes, "auth.locked")
    falhas = await _trilha(sessoes, "auth.login_failed")

    assert (bloqueio["actor_type"], bloqueio["origin"]) == ("sistema", "api")
    assert bloqueio["actor_user_id"] is None
    assert (bloqueio["entity_type"], bloqueio["entity_id"]) == ("usuario", str(joao))
    assert {(f["actor_type"], f["actor_user_id"]) for f in falhas} == {("usuario", joao)}


async def test_login_registra_papeis(cliente: httpx.AsyncClient, sessoes: Sessoes) -> None:
    """013/R1.4: o `auth.login` registra os papéis efetivos do usuário naquele momento."""
    maria = await usuario_local(sessoes, "maria")
    await _atribuir(sessoes, maria, "GESTOR_DADOS")
    await _atribuir(sessoes, maria, "AUDITOR")

    confirmado, _ = await cadastrar_e_entrar(cliente, "maria")

    assert confirmado.status_code == 200, confirmado.text
    [evento] = await _trilha(sessoes, "auth.login")
    assert (evento["actor_type"], evento["origin"]) == ("usuario", "api")
    assert evento["actor_user_id"] == maria
    assert sorted(evento["actor_roles"]) == ["AUDITOR", "GESTOR_DADOS"]


async def _atribuir(sessoes: Sessoes, usuario: UUID, papel: str) -> None:
    async with sessoes() as sessao, sessao.begin():
        await sessao.execute(
            text(
                "INSERT INTO role_assignments (id, user_id, role_id, scope_type, scope_id, origin)"
                " SELECT :id, :usuario, id, 'global', NULL, 'direct' FROM roles WHERE code = :papel"
            ),
            {"id": uuid7(), "usuario": usuario, "papel": papel},
        )


async def test_evento_de_negocio_tem_user_agent_e_ip(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R3.2, R3.4, R3.5 (T3): o evento grava o IP da conexão e o User-Agent já limpo; o
    `X-Forwarded-For` e o `X-Real-IP` de um cliente que não é proxy confiável não valem."""
    gestor = await logado(sessoes, ("GESTOR_DADOS", GLOBAL))
    corpo = {
        "nome": "CAPS Espaço Verde",
        "tipo_unidade_id": await id_pelo_codigo(sessoes, "tipo_unidade", "CAPS_II"),
        "distrito_id": await id_pelo_codigo(sessoes, "distrito", "DS-I"),
        "cep": "50010100",
        "endereco": "Rua da Aurora, 10",
        "status": "ativa",
    }
    cabecalhos = {
        "User-Agent": "Navegador/1.0\tcom\x7fcontrole " + "x" * 300,
        "X-Forwarded-For": "6.6.6.6",
        "X-Real-IP": "7.7.7.7",
    }

    resposta = await cliente.post(
        "/api/v1/unidades", json=corpo, headers=bearer(app, gestor) | cabecalhos
    )

    assert resposta.status_code == 201, resposta.text
    [evento] = await _trilha(sessoes, "unidade.criada")
    assert evento["ip"] == "127.0.0.1"  # endereço da conexão do cliente de teste (httpx)
    assert evento["user_agent"].startswith("Navegador/1.0comcontrole x")
    assert len(evento["user_agent"]) == 200
    assert "user_agent" not in evento["metadata"]


async def test_evento_de_autenticacao_tem_user_agent_na_coluna(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R3.4 (T3): as rotas de autenticação usam o mesmo helper; o User-Agent vai para a
    coluna, e não mais para `metadata.user_agent`."""
    await cliente.post(
        "/api/v1/auth/login",
        json={"username": "ninguem", "password": "x"},
        headers={"User-Agent": "curl/8.0\r\n", "X-Forwarded-For": "6.6.6.6"},
    )

    [evento] = await _trilha(sessoes, "auth.login_failed")
    assert (evento["ip"], evento["user_agent"]) == ("127.0.0.1", "curl/8.0")
    assert "user_agent" not in evento["metadata"]
