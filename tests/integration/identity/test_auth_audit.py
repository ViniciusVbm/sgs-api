"""Rate limit do login e auditoria dos eventos de acesso (002/T7)."""

import httpx

from tests.integration.acesso import Sessoes, eventos
from tests.integration.identity.autenticacao import cadastrar_e_entrar, login, usuario_local


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
    """R4.1: login, falha, 2FA cadastrado, bloqueio, logout; nunca senha nem token."""
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
        assert "user_agent" in registrados[0]["metadata"]
    todos = str([await eventos(sessoes, a) for a in ("auth.login", "auth.login_failed")])
    assert "senha" not in todos
    assert confirmado.json()["access_token"] not in todos
