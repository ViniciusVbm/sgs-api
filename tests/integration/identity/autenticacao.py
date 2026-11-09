"""Ajudantes dos testes de autenticação: usuário local com senha e o fluxo até os tokens."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import httpx
import pyotp

from src.core.ids import uuid7
from src.modules.identity.domain.users import User, UserSource
from src.modules.identity.infrastructure.passwords import Argon2PasswordHasher
from src.modules.identity.infrastructure.repository import SqlUserRepository
from tests.integration.acesso import Sessoes

SENHA = "senha-forte-de-teste-123"
ORIGEM = "https://sgs.teste"
_HASHER = Argon2PasswordHasher()


async def usuario_local(sessoes: Sessoes, username: str = "maria", *, ativo: bool = True) -> UUID:
    usuario = User(
        id=uuid7(),
        username=username,
        display_name=username.title(),
        source=UserSource.LOCAL,
        password_hash=_HASHER.hash(SENHA),
        is_active=ativo,
    )
    async with sessoes() as sessao, sessao.begin():
        await SqlUserRepository(sessao).add(usuario)
    return usuario.id


async def login(cliente: httpx.AsyncClient, username: str, senha: str = SENHA) -> httpx.Response:
    return await cliente.post("/api/v1/auth/login", json={"username": username, "password": senha})


def segredo_da_uri(uri: str) -> str:
    return parse_qs(urlsplit(uri).query)["secret"][0]


def codigo(segredo: str, *, adiante: int = 0) -> str:
    """Código TOTP do passo atual mais `adiante` passos (dentro da janela de ±1, R2.4)."""
    return pyotp.TOTP(segredo).at(datetime.now(UTC) + timedelta(seconds=30 * adiante))


async def cadastrar_e_entrar(
    cliente: httpx.AsyncClient, username: str, senha: str = SENHA
) -> tuple[httpx.Response, str]:
    """login → enroll → confirm; devolve a resposta do confirm e o segredo TOTP."""
    desafio = (await login(cliente, username, senha)).json()["mfa_token"]
    uri = (await cliente.post("/api/v1/auth/mfa/enroll", json={"mfa_token": desafio})).json()[
        "otpauth_uri"
    ]
    segredo = segredo_da_uri(uri)
    confirmado = await cliente.post(
        "/api/v1/auth/mfa/confirm", json={"mfa_token": desafio, "code": codigo(segredo)}
    )
    return confirmado, segredo
