"""Cadastro e verificação do TOTP (002/T5): segredo cifrado, janela, reuso, 5 tentativas."""

import httpx
from sqlalchemy import text

from tests.integration.acesso import Sessoes
from tests.integration.identity.autenticacao import (
    cadastrar_e_entrar,
    codigo,
    login,
    usuario_local,
)


async def test_cadastro_ativa_o_2fa_e_emite_os_tokens(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R2.1, R2.2, R2.5: segredo só cifrado no banco; confirmação emite access e refresh."""
    usuario = await usuario_local(sessoes)

    confirmado, segredo = await cadastrar_e_entrar(cliente, "maria")
    async with sessoes() as sessao:
        linha = (
            await sessao.execute(
                text("SELECT mfa_enabled, mfa_secret_enc FROM users WHERE id = :id"),
                {"id": usuario},
            )
        ).one()

    assert confirmado.status_code == 200, confirmado.text
    assert confirmado.json()["access_token"]
    assert "sgs_refresh" in confirmado.cookies
    assert linha.mfa_enabled is True
    assert segredo not in linha.mfa_secret_enc
    assert linha.mfa_secret_enc.startswith("v1:")


async def test_com_2fa_o_login_pede_o_codigo_e_recusa_o_reuso(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R1.1, R2.3, R2.4: o código do passo já usado no cadastro não vale de novo."""
    await usuario_local(sessoes)
    _, segredo = await cadastrar_e_entrar(cliente, "maria")

    desafio = await login(cliente, "maria")
    reuso = await cliente.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": desafio.json()["mfa_token"], "code": codigo(segredo)},
    )
    novo = await cliente.post(
        "/api/v1/auth/mfa/verify",
        json={"mfa_token": desafio.json()["mfa_token"], "code": codigo(segredo, adiante=1)},
    )

    assert desafio.json()["mfa_required"] is True
    assert reuso.status_code == 401
    assert novo.status_code == 200, novo.text


async def test_cinco_codigos_errados_invalidam_o_mfa_token(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R2.6."""
    await usuario_local(sessoes)
    _, segredo = await cadastrar_e_entrar(cliente, "maria")
    desafio = (await login(cliente, "maria")).json()["mfa_token"]
    for _ in range(5):
        await cliente.post("/api/v1/auth/mfa/verify", json={"mfa_token": desafio, "code": "000000"})

    depois = await cliente.post(
        "/api/v1/auth/mfa/verify", json={"mfa_token": desafio, "code": codigo(segredo, adiante=1)}
    )

    assert depois.status_code == 401


async def test_mfa_token_de_cadastro_nao_serve_para_verificar(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    await usuario_local(sessoes)
    desafio = (await login(cliente, "maria")).json()["mfa_token"]

    resposta = await cliente.post(
        "/api/v1/auth/mfa/verify", json={"mfa_token": desafio, "code": "123456"}
    )

    assert resposta.status_code == 401
