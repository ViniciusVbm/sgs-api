"""Portas do módulo de identidade.

Os repositórios trabalham sobre a transação de quem os usa: quem chama abre, confirma ou desfaz.
"""

from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.sessions import AuthSession, RefreshToken
from src.modules.identity.domain.users import User


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_username(self, username: str) -> User | None:
        """Busca sem diferenciar maiúsculas de minúsculas (o nome é normalizado)."""
        ...


class SessionRepository(Protocol):
    async def add(self, session: AuthSession) -> None: ...

    async def get_by_id(self, session_id: UUID) -> AuthSession | None: ...


class RefreshTokenRepository(Protocol):
    async def add(self, token: RefreshToken) -> None: ...

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Busca pelo SHA-256 do token (`hash_refresh_token`), nunca pelo valor em claro."""
        ...
