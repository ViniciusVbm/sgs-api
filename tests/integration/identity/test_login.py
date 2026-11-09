"""`POST /auth/login` (002/T3): senha Argon2id, mensagem e tempo iguais, bloqueio, desativado."""

import time

import httpx
from sqlalchemy import text

from tests.integration.acesso import Sessoes
from tests.integration.identity.autenticacao import SENHA, login, usuario_local


async def test_senha_certa_sem_2fa_pede_o_cadastro_do_2fa(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R1.2: sem 2FA cadastrado, `mfa_enrollment_required` e um `mfa_token`; sem tokens."""
    await usuario_local(sessoes)

    resposta = await login(cliente, "MARIA")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["mfa_enrollment_required"] is True
    assert corpo["mfa_required"] is False
    assert corpo["mfa_token"]
    assert corpo["access_token"] is None
    assert "sgs_refresh" not in resposta.cookies


async def test_usuario_inexistente_e_senha_errada_dao_o_mesmo_401(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R1.3: mesma mensagem e tempo semelhante (tolerância ampla)."""
    await usuario_local(sessoes)

    inicio = time.perf_counter()
    errada = await login(cliente, "maria", "senha-errada-qualquer")
    meio = time.perf_counter()
    inexistente = await login(cliente, "ninguem", "senha-errada-qualquer")
    fim = time.perf_counter()

    assert errada.status_code == inexistente.status_code == 401
    assert errada.json()["detail"] == inexistente.json()["detail"]
    assert abs((meio - inicio) - (fim - meio)) < 0.5


async def test_cinco_falhas_bloqueiam_por_quinze_minutos(
    cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R1.4: depois de 5 falhas seguidas, nem a senha certa entra."""
    usuario = await usuario_local(sessoes)
    for _ in range(5):
        await login(cliente, "maria", "senha-errada-qualquer")

    bloqueado = await login(cliente, "maria", SENHA)
    async with sessoes() as sessao:
        minutos = await sessao.scalar(
            text("SELECT extract(epoch FROM locked_until - now()) / 60 FROM users WHERE id = :id"),
            {"id": usuario},
        )

    assert bloqueado.status_code == 401
    assert 14 < float(minutos) <= 15


async def test_usuario_desativado_e_recusado(cliente: httpx.AsyncClient, sessoes: Sessoes) -> None:
    """R1.6."""
    await usuario_local(sessoes, "inativa", ativo=False)

    resposta = await login(cliente, "inativa")

    assert resposta.status_code == 401


async def test_senha_guardada_so_como_argon2id(sessoes: Sessoes) -> None:
    """R1.7."""
    usuario = await usuario_local(sessoes)
    async with sessoes() as sessao:
        hash_ = await sessao.scalar(
            text("SELECT password_hash FROM users WHERE id = :id"), {"id": usuario}
        )

    assert hash_.startswith("$argon2id$")
    assert SENHA not in hash_
