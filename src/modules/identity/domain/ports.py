"""Portas do módulo de identidade.

Os repositórios trabalham sobre a transação de quem os usa: quem chama abre, confirma ou desfaz.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.identity.domain.login import EstadoDeLogin
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


class LoginStateRepository(Protocol):
    """Contadores de falha, bloqueio e estado do 2FA em `users` (002, design § Modelo)."""

    async def estado(self, user_id: UUID) -> EstadoDeLogin | None: ...

    async def registrar_falha(self, user_id: UUID, agora: datetime) -> EstadoDeLogin:
        """Incrementa `failed_logins`; na 5ª seguida, bloqueia por 15 min e zera (R1.4)."""
        ...

    async def registrar_sucesso(self, user_id: UUID, agora: datetime) -> None:
        """Zera as falhas, tira o bloqueio e grava `last_login_at`."""
        ...

    async def novo_desafio(self, user_id: UUID, jti: UUID) -> None:
        """Troca o `mfa_challenge_jti` e zera as tentativas: só o `mfa_token` novo vale (R2.6)."""
        ...

    async def falha_de_mfa(self, user_id: UUID) -> int:
        """Incrementa `mfa_failed_attempts` e devolve o total; na 5ª, limpa o desafio (R2.6)."""
        ...

    async def gravar_segredo(self, user_id: UUID, segredo_cifrado: str) -> None: ...

    async def concluir_mfa(self, user_id: UUID, passo: int, *, ativar: bool) -> None:
        """Grava o passo usado (anti-reuso), limpa o desafio e, no cadastro, ativa o 2FA."""
        ...


class SessionRevoker(Protocol):
    async def revogar(self, session_id: UUID, agora: datetime) -> None:
        """Revoga a sessão e os refresh tokens dela (R3.5, R3.7)."""
        ...


class RefreshTokenWriter(Protocol):
    async def marcar_usado(self, token_id: UUID, agora: datetime) -> bool:
        """Marca o refresh como usado, só se ainda não estava; `False` se outro já usou."""
        ...
