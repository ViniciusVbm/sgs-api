"""Rate limit do login e auditoria dos eventos de acesso (002/T7)."""

import httpx
from sqlalchemy import text

from tests.integration.acesso import Sessoes, eventos
from tests.integration.identity.autenticacao import (
    cadastrar_e_entrar,
    codigo,
    login,
    usuario_local,
)


async def test_login_limitado_a_dez_por_minuto_por_ip(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R1.5."""
    respostas = [await login(cliente, "ninguem", "x") for _ in range(11)]

    assert [r.status_code for r in respostas[:10]] == [401] * 10
    assert respostas[10].status_code == 429


async def test_eventos_de_acesso_auditados_com_ip_e_user_agent(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R4.1: login, falha, 2FA cadastrado, bloqueio, logout; nunca senha nem token. IP e User-Agent
    em todos (013/R3.4)."""
    await usuario_local(sessoes)
    await usuario_local(sessoes, "joao")
    await login(cliente, "maria", "senha-errada")
    confirmado, _ = await cadastrar_e_entrar(cliente, "maria")
    for _ in range(5):
        await login(cliente, "joao", "senha-errada")
    await cliente.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {confirmado.json()['access_token']}"},
    )

    for acao in (
        "auth.login",
        "auth.login_failed",
        "auth.mfa_enrolled",
        "auth.locked",
        "auth.logout",
    ):
        registrados = await eventos(sessoes, acao)
        assert registrados, acao
    # 013/R3.4 (T3): o User-Agent e o IP vão para as colunas próprias de cada evento de acesso.
    async with sessoes() as sessao:
        sem_origem = await sessao.scalar(
            text(
                "SELECT count(*) FROM audit_log"
                " WHERE action LIKE 'auth.%' AND (user_agent IS NULL OR ip IS NULL)"
            )
        )
    assert sem_origem == 0
    todos = str([await eventos(sessoes, a) for a in ("auth.login", "auth.login_failed")])
    assert "senha" not in todos
    assert confirmado.json()["access_token"] not in todos


async def _resultados(sessoes: Sessoes, acao: str) -> list[tuple[str, str | None]]:
    async with sessoes() as sessao:
        linhas = await sessao.execute(
            text("SELECT result, result_reason FROM audit_log WHERE action = :acao ORDER BY id"),
            {"acao": acao},
        )
        return [(linha.result, linha.result_reason) for linha in linhas]


async def test_login_falho_tem_resultado_failure(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R4.1, R4.2: login falho é `failure`/`autenticacao` (usuário inexistente e senha
    errada); o login que deu certo e o bloqueio são `success`, sem categoria."""
    await usuario_local(sessoes)
    await usuario_local(sessoes, "joao")
    await login(cliente, "ninguem", "x")
    await login(cliente, "maria", "senha-errada")
    await cadastrar_e_entrar(cliente, "maria")
    for _ in range(5):
        await login(cliente, "joao", "senha-errada")

    falhas = await _resultados(sessoes, "auth.login_failed")

    assert len(falhas) == 7
    assert set(falhas) == {("failure", "autenticacao")}
    assert await _resultados(sessoes, "auth.login") == [("success", None)]
    assert await _resultados(sessoes, "auth.locked") == [("success", None)]


async def test_mfa_falho_e_auditado(cliente: httpx.AsyncClient, sessoes: Sessoes) -> None:
    """013/R4.2: código errado e código reutilizado gravam `auth.mfa_failed` com `failure`/
    `autenticacao`, as tentativas e se foi reuso; nunca o código."""
    await usuario_local(sessoes)
    _, segredo = await cadastrar_e_entrar(cliente, "maria")
    desafio = (await login(cliente, "maria")).json()["mfa_token"]

    errado = await cliente.post(
        "/api/v1/auth/mfa/verify", json={"mfa_token": desafio, "code": "000000"}
    )
    reuso = await cliente.post(
        "/api/v1/auth/mfa/verify", json={"mfa_token": desafio, "code": codigo(segredo)}
    )

    assert (errado.status_code, reuso.status_code) == (401, 401)
    async with sessoes() as sessao:
        linhas = (
            await sessao.execute(
                text(
                    "SELECT result, result_reason, metadata FROM audit_log"
                    " WHERE action = 'auth.mfa_failed' ORDER BY id"
                )
            )
        ).all()
    assert [(linha.result, linha.result_reason) for linha in linhas] == [
        ("failure", "autenticacao"),
        ("failure", "autenticacao"),
    ]
    assert [(linha.metadata["reuso"], linha.metadata["tentativas"]) for linha in linhas] == [
        (False, 1),
        (True, 2),
    ]
    assert codigo(segredo) not in str([linha.metadata for linha in linhas])
