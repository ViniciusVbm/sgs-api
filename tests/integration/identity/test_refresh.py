"""Refresh rotativo, reuso, anti-CSRF e logout (002/T6)."""

import httpx
from sqlalchemy import text

from tests.integration.acesso import Sessoes, eventos
from tests.integration.identity.autenticacao import ORIGEM, cadastrar_e_entrar, usuario_local

CABECALHOS = {"X-Requested-With": "sgs", "Origin": ORIGEM}


async def test_cookie_do_refresh_tem_os_atributos_da_spec(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R3.3."""
    await usuario_local(sessoes)
    confirmado, _ = await cadastrar_e_entrar(cliente, "maria")

    cookie = confirmado.headers["set-cookie"].lower()

    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api/v1/auth" in cookie


async def test_refresh_rotativo_e_reuso_revoga_a_sessao(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R3.4, R3.5: o novo par vale; reapresentar o antigo revoga tudo e audita."""
    await usuario_local(sessoes)
    confirmado, _ = await cadastrar_e_entrar(cliente, "maria")
    antigo = confirmado.cookies["sgs_refresh"]

    novo = await cliente.post("/api/v1/auth/refresh", headers=CABECALHOS)
    novo_cookie = novo.cookies["sgs_refresh"]
    cliente.cookies.clear()
    cliente.cookies.set("sgs_refresh", antigo, domain="teste.local", path="/api/v1/auth")
    reuso = await cliente.post("/api/v1/auth/refresh", headers=CABECALHOS)
    cliente.cookies.clear()
    cliente.cookies.set("sgs_refresh", novo_cookie, domain="teste.local", path="/api/v1/auth")
    depois = await cliente.post("/api/v1/auth/refresh", headers=CABECALHOS)
    acesso = await cliente.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {novo.json()['access_token']}"}
    )

    assert novo.status_code == 200
    assert novo_cookie != antigo
    assert reuso.status_code == 401
    assert depois.status_code == 401  # a sessão inteira foi revogada
    assert acesso.status_code == 401
    assert len(await eventos(sessoes, "auth.refresh_reuse")) == 1


async def test_refresh_exige_os_cabecalhos_anti_csrf(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R3.6."""
    await usuario_local(sessoes)
    await cadastrar_e_entrar(cliente, "maria")

    sem_cabecalho = await cliente.post("/api/v1/auth/refresh", headers={"Origin": ORIGEM})
    outra_origem = await cliente.post(
        "/api/v1/auth/refresh", headers={"X-Requested-With": "sgs", "Origin": "https://mal.com"}
    )

    assert sem_cabecalho.status_code == 403
    assert outra_origem.status_code == 403


async def test_logout_revoga_a_sessao_e_apaga_o_cookie(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R3.7, R3.8."""
    usuario = await usuario_local(sessoes)
    confirmado, _ = await cadastrar_e_entrar(cliente, "maria")
    bearer = {"Authorization": f"Bearer {confirmado.json()['access_token']}"}

    saida = await cliente.post("/api/v1/auth/logout", headers=bearer)
    depois = await cliente.get("/api/v1/me", headers=bearer)
    async with sessoes() as sessao:
        revogadas = await sessao.scalar(
            text("SELECT count(*) FROM sessions WHERE user_id = :id AND revoked_at IS NOT NULL"),
            {"id": usuario},
        )

    assert saida.status_code == 204
    assert (
        'sgs_refresh=""' in saida.headers["set-cookie"]
        or "max-age=0" in saida.headers["set-cookie"].lower()
    )
    assert depois.status_code == 401
    assert revogadas == 1
