"""Repositórios de identidade sobre a sessão SQLAlchemy de quem os usa (SQLAlchemy Core)."""

from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.domain.sessions import AuthSession, RefreshToken
from src.modules.identity.domain.users import User, normalize_username
from src.modules.identity.infrastructure.tables import refresh_tokens, sessions, users

# Só as colunas que o `User` conhece; o segredo TOTP fica de fora até a T5.
_USER_COLUMNS = (
    users.c.id,
    users.c.username,
    users.c.display_name,
    users.c.source,
    users.c.password_hash,
    users.c.email,
    users.c.external_id,
    users.c.is_active,
)
_SESSION_COLUMNS = (
    sessions.c.id,
    sessions.c.user_id,
    sessions.c.amr,
    sessions.c.created_at,
    sessions.c.ip,
    sessions.c.user_agent,
    sessions.c.revoked_at,
)
_REFRESH_COLUMNS = (
    refresh_tokens.c.id,
    refresh_tokens.c.session_id,
    refresh_tokens.c.family_id,
    refresh_tokens.c.token_hash,
    refresh_tokens.c.expires_at,
    refresh_tokens.c.used_at,
    refresh_tokens.c.revoked_at,
)


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        await self._session.execute(
            insert(users).values(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                source=user.source.value,
                password_hash=user.password_hash,
                email=user.email,
                external_id=user.external_id,
                is_active=user.is_active,
            )
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.execute(select(*_USER_COLUMNS).where(users.c.id == user_id))
        row = result.mappings().one_or_none()
        return None if row is None else User(**row)

    async def get_by_username(self, username: str) -> User | None:
        result = await self._session.execute(
            select(*_USER_COLUMNS).where(users.c.username == normalize_username(username))
        )
        row = result.mappings().one_or_none()
        return None if row is None else User(**row)


class SqlSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, session: AuthSession) -> None:
        await self._session.execute(
            insert(sessions).values(
                id=session.id,
                user_id=session.user_id,
                amr=session.amr,
                created_at=session.created_at,
                ip=session.ip,
                user_agent=session.user_agent,
                revoked_at=session.revoked_at,
            )
        )

    async def get_by_id(self, session_id: UUID) -> AuthSession | None:
        result = await self._session.execute(
            select(*_SESSION_COLUMNS).where(sessions.c.id == session_id)
        )
        row = result.mappings().one_or_none()
        return None if row is None else AuthSession(**row)


class SqlRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, token: RefreshToken) -> None:
        await self._session.execute(
            insert(refresh_tokens).values(
                id=token.id,
                session_id=token.session_id,
                family_id=token.family_id,
                token_hash=token.token_hash,
                expires_at=token.expires_at,
                used_at=token.used_at,
                revoked_at=token.revoked_at,
            )
        )

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(*_REFRESH_COLUMNS).where(refresh_tokens.c.token_hash == token_hash)
        )
        row = result.mappings().one_or_none()
        return None if row is None else RefreshToken(**row)
