"""Regras do login local (spec 002, R1.4, R2.6 e R3.3)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

FALHAS_PARA_BLOQUEIO = 5  # R1.4
DURACAO_DO_BLOQUEIO = timedelta(minutes=15)  # R1.4
TENTATIVAS_DE_MFA = 5  # R2.6
VALIDADE_DO_REFRESH = timedelta(hours=8)  # R3.3

MENSAGEM_DE_CREDENCIAIS = "Usuário ou senha inválidos."
"""A mesma para usuário inexistente, senha errada, usuário desativado e bloqueado (R1.3, R1.6)."""


@dataclass(frozen=True, slots=True)
class EstadoDeLogin:
    """O que o login lê do usuário além do `User`: bloqueio, 2FA e o desafio em andamento."""

    user_id: UUID
    failed_logins: int
    locked_until: datetime | None
    mfa_enabled: bool
    mfa_secret_enc: str | None
    mfa_last_step: int | None
    mfa_challenge_jti: UUID | None
    mfa_failed_attempts: int

    def bloqueado(self, agora: datetime) -> bool:
        return self.locked_until is not None and self.locked_until > agora
