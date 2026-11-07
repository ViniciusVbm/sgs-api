"""Repositórios de identidade sobre o PostgreSQL: usuário, sessão e refresh token (002/T2)."""

import hashlib
import secrets
from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.ids import uuid7
from src.modules.identity.domain.sessions import AuthSession, hash_refresh_token
from src.modules.identity.domain.users import User
from src.modules.identity.infrastructure.repository import (
    SqlRefreshTokenRepository,
    SqlSessionRepository,
    SqlUserRepository,
)
from tests.factories import (
    ARGON2ID_DE_TESTE,
    HASH_BCRYPT,
    make_auth_session,
    make_refresh_token,
    make_user,
)
from tests.integration.postgres import BancoDeTeste, motor

SEM_PRIVILEGIO = "42501"  # SQLSTATE insufficient_privilege

INSERIR_USUARIO_LOCAL = text(
    "INSERT INTO users (id, username, display_name, source, password_hash)"
    " VALUES (:id, 'teste', 'Teste', 'local', :senha)"
)
INSERIR_REFRESH = text(
    "INSERT INTO refresh_tokens (id, session_id, family_id, token_hash, expires_at)"
    " VALUES (:id, :sessao, :familia, :token, now() + interval '8 hours')"
)


@pytest.fixture
async def sessoes(banco: BancoDeTeste) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Sessões com o login da API (papel sgs_app), como em produção."""
    engine = motor(banco.url_api)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _gravar_usuario(sessoes: async_sessionmaker[AsyncSession]) -> User:
    usuario = make_user()
    async with sessoes() as sessao, sessao.begin():
        await SqlUserRepository(sessao).add(usuario)
    return usuario


async def _gravar_sessao_de_login(sessoes: async_sessionmaker[AsyncSession]) -> AuthSession:
    usuario = await _gravar_usuario(sessoes)
    sessao_de_login = make_auth_session(user_id=usuario.id, ip="10.0.0.1", user_agent="Firefox")
    async with sessoes() as sessao, sessao.begin():
        await SqlSessionRepository(sessao).add(sessao_de_login)
    return sessao_de_login


async def test_usuario_local_volta_do_banco_com_o_hash_argon2id(
    sessoes: async_sessionmaker[AsyncSession],
) -> None:
    """002/R1.7"""
    usuario = await _gravar_usuario(sessoes)

    async with sessoes() as sessao:
        repositorio = SqlUserRepository(sessao)
        assert await repositorio.get_by_id(usuario.id) == usuario
        assert await repositorio.get_by_username(f"  {usuario.username.upper()} ") == usuario
        assert await repositorio.get_by_id(uuid7()) is None
        assert await repositorio.get_by_username("ninguem") is None
        gravado = await sessao.scalar(
            text("SELECT password_hash FROM users WHERE id = :id"), {"id": usuario.id}
        )
    assert gravado == ARGON2ID_DE_TESTE


@pytest.mark.parametrize(
    "senha",
    ["senha-em-texto-puro", HASH_BCRYPT, "$argon2id$sem-o-formato-phc"],
    ids=["texto-puro", "bcrypt", "prefixo-sem-formato"],
)
async def test_banco_recusa_senha_que_nao_e_hash_argon2id(
    sessoes: async_sessionmaker[AsyncSession], senha: str
) -> None:
    """002/R1.7: a restrição vale até para quem grava sem passar pelo domínio."""
    with pytest.raises(IntegrityError, match='"ck_users_senha_argon2id"'):
        async with sessoes() as sessao, sessao.begin():
            await sessao.execute(INSERIR_USUARIO_LOCAL, {"id": uuid7(), "senha": senha})


async def test_banco_recusa_email_com_maiusculas(
    sessoes: async_sessionmaker[AsyncSession],
) -> None:
    """002/T2: a unicidade do e-mail não pode depender de maiúsculas."""
    with pytest.raises(IntegrityError, match='"ck_users_email_minusculo"'):
        async with sessoes() as sessao, sessao.begin():
            await sessao.execute(
                text(
                    "INSERT INTO users (id, username, display_name, source, password_hash, email)"
                    " VALUES (:id, 'teste', 'Teste', 'local', :senha, 'Maria@Example.org')"
                ),
                {"id": uuid7(), "senha": ARGON2ID_DE_TESTE},
            )


async def test_api_nao_apaga_usuario(sessoes: async_sessionmaker[AsyncSession]) -> None:
    """002/T2: usuário nunca é apagado, só desativado (docs/architecture/modelo-dados.md § 1)."""
    usuario = await _gravar_usuario(sessoes)

    with pytest.raises(DBAPIError) as erro:
        async with sessoes() as sessao, sessao.begin():
            await sessao.execute(text("DELETE FROM users WHERE id = :id"), {"id": usuario.id})

    assert getattr(erro.value.orig, "sqlstate", None) == SEM_PRIVILEGIO


async def test_sessao_de_login_volta_do_banco(sessoes: async_sessionmaker[AsyncSession]) -> None:
    """002/T2"""
    sessao_de_login = await _gravar_sessao_de_login(sessoes)

    async with sessoes() as sessao:
        repositorio = SqlSessionRepository(sessao)
        assert await repositorio.get_by_id(sessao_de_login.id) == sessao_de_login
        assert await repositorio.get_by_id(uuid7()) is None


async def test_refresh_token_e_guardado_so_como_hash(
    sessoes: async_sessionmaker[AsyncSession],
) -> None:
    """002/R3.3"""
    sessao_de_login = await _gravar_sessao_de_login(sessoes)
    token = secrets.token_urlsafe(32)
    refresh = make_refresh_token(
        session_id=sessao_de_login.id, token_hash=hash_refresh_token(token)
    )
    async with sessoes() as sessao, sessao.begin():
        await SqlRefreshTokenRepository(sessao).add(refresh)

    async with sessoes() as sessao:
        repositorio = SqlRefreshTokenRepository(sessao)
        assert await repositorio.get_by_hash(hash_refresh_token(token)) == refresh
        assert await repositorio.get_by_hash(hash_refresh_token("outro-token")) is None
        resultado = await sessao.execute(
            text("SELECT * FROM refresh_tokens WHERE id = :id"), {"id": refresh.id}
        )
        linha = resultado.mappings().one()
    assert linha["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
    assert all(token not in str(valor) for valor in linha.values())


async def test_banco_recusa_refresh_token_que_nao_e_hash_sha256(
    sessoes: async_sessionmaker[AsyncSession],
) -> None:
    """002/R3.3: a restrição vale até para quem grava sem passar pelo domínio."""
    sessao_de_login = await _gravar_sessao_de_login(sessoes)
    valores: dict[str, UUID | str] = {
        "id": uuid7(),
        "sessao": sessao_de_login.id,
        "familia": uuid7(),
        "token": secrets.token_urlsafe(32),
    }

    with pytest.raises(IntegrityError, match='"ck_refresh_tokens_token_hash_sha256"'):
        async with sessoes() as sessao, sessao.begin():
            await sessao.execute(INSERIR_REFRESH, valores)
