"""Sessão de login e refresh token (spec 002; docs/architecture/modelo-dados.md § 1).

R3.3: o refresh token é opaco e só o SHA-256 dele é guardado. Quem lê o banco não consegue usar
o token, e o repositório nunca recebe o valor em claro: só o `RefreshToken`, que carrega o hash.
"""

import hashlib
import ipaddress
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from src.core.errors import DomainValidationError, FieldError

AMR_MAX = 20
USER_AGENT_MAX = 512
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


def hash_refresh_token(token: str) -> str:
    """SHA-256 do token opaco, em hexadecimal minúsculo: é o que vai para o banco."""
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class AuthSession:
    """Sessão aberta por um login; o `id` é o `sid` do access token."""

    id: UUID
    user_id: UUID
    amr: str
    created_at: datetime
    ip: str | None = None
    user_agent: str | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.amr or len(self.amr) > AMR_MAX:
            raise _invalid("Sessão inválida.", "amr", "Método de autenticação inválido.")
        object.__setattr__(self, "created_at", _utc(self.created_at, "created_at"))
        if self.revoked_at is not None:
            object.__setattr__(self, "revoked_at", _utc(self.revoked_at, "revoked_at"))
        if self.ip is not None:
            try:
                endereco = ipaddress.ip_address(self.ip)
            except ValueError:
                raise _invalid("Sessão inválida.", "ip", "IP inválido.") from None
            # A zona do IPv6 (`fe80::1%eth0`) só vale na máquina local e não tem limite de tamanho.
            if isinstance(endereco, ipaddress.IPv6Address) and endereco.scope_id:
                endereco = ipaddress.IPv6Address(int(endereco))
            object.__setattr__(self, "ip", str(endereco))
        if self.user_agent is not None:
            # O cabeçalho vem do cliente: corta no tamanho da coluna em vez de recusar o login.
            object.__setattr__(self, "user_agent", self.user_agent[:USER_AGENT_MAX])


@dataclass(frozen=True)
class RefreshToken:
    """Registro de um refresh token emitido. O token em si fica só com o cliente (cookie)."""

    id: UUID
    session_id: UUID
    family_id: UUID
    token_hash: str = field(repr=False)
    expires_at: datetime
    used_at: datetime | None = None
    revoked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not _SHA256_HEX.fullmatch(self.token_hash):
            raise _invalid(
                "Refresh token inválido.",
                "token_hash",
                "Guarde só o SHA-256 do token (use hash_refresh_token).",
            )
        object.__setattr__(self, "expires_at", _utc(self.expires_at, "expires_at"))
        for campo in ("used_at", "revoked_at"):
            valor = getattr(self, campo)
            if valor is not None:
                object.__setattr__(self, campo, _utc(valor, campo))


def _utc(valor: datetime, campo: str) -> datetime:
    if valor.tzinfo is None:
        raise _invalid("Data inválida.", campo, "Informe o fuso horário.")
    return valor.astimezone(UTC)


def _invalid(detalhe: str, campo: str, mensagem: str) -> DomainValidationError:
    return DomainValidationError(detalhe, errors=[FieldError(campo=campo, mensagem=mensagem)])
