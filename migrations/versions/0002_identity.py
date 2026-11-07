"""identity: users, sessions e refresh_tokens (spec 002, T2; R1.7 e R3.3).

Colunas de docs/architecture/modelo-dados.md § 1, mais `users.mfa_last_step` e o desafio de MFA
da R2.6 (`mfa_challenge_jti`, `mfa_failed_attempts`), conforme o design da 002. As restrições
garantem, até para quem grava sem passar pelo domínio, que a senha só entra como hash Argon2id e o
refresh token só como SHA-256.

Os nomes das CHECKs vão em `op.f()`: sem isso, o Alembic aplica a convenção do `metadata` por
cima do nome completo e grava `ck_users_ck_users_...` (ver 0001_1).

Revision ID: 0002
Revises: 0001_1
Create Date: 2026-11-06
"""

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Formato PHC: $argon2id$v=19$m=<memória KiB>,t=<iterações>,p=<paralelismo>$<sal>$<hash>
ARGON2ID_PHC = r"^\$argon2id\$v=19\$m=[0-9]+,t=[0-9]+,p=[0-9]+\$[A-Za-z0-9+/]+\$[A-Za-z0-9+/]+$"


def _timestamps() -> tuple[sa.Column[datetime], sa.Column[datetime]]:
    return (
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid, nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("external_id", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("mfa_secret_enc", sa.String(255), nullable=True),
        sa.Column("mfa_last_step", sa.BigInteger, nullable=True),
        # R2.6: `jti` do mfa_token mais recente e os códigos errados contra ele.
        sa.Column("mfa_challenge_jti", sa.Uuid, nullable=True),
        sa.Column("mfa_failed_attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("failed_logins", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("source", "external_id", name="uq_users_source_external_id"),
        sa.CheckConstraint(
            "source IN ('local', 'ldap', 'oidc')", name=op.f("ck_users_origem_valida")
        ),
        sa.CheckConstraint("username = lower(username)", name=op.f("ck_users_username_minusculo")),
        sa.CheckConstraint(
            f"password_hash ~ '{ARGON2ID_PHC}'", name=op.f("ck_users_senha_argon2id")
        ),
        # Conta local tem senha; conta de diretório (LDAP, OIDC) tem só o DN ou o `sub`.
        sa.CheckConstraint(
            "(source = 'local' AND password_hash IS NOT NULL AND external_id IS NULL)"
            " OR (source <> 'local' AND password_hash IS NULL AND external_id IS NOT NULL)",
            name=op.f("ck_users_credencial_conforme_origem"),
        ),
        sa.CheckConstraint(
            "NOT mfa_enabled OR mfa_secret_enc IS NOT NULL", name=op.f("ck_users_mfa_com_segredo")
        ),
        sa.CheckConstraint("failed_logins >= 0", name=op.f("ck_users_falhas_nao_negativas")),
        sa.CheckConstraint(
            "mfa_failed_attempts >= 0", name=op.f("ck_users_tentativas_mfa_nao_negativas")
        ),
    )
    # Usuário nunca é apagado, só desativado (modelo-dados.md § 1).
    op.execute("REVOKE DELETE ON users FROM sgs_app")

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid, nullable=False),
        sa.Column("user_id", sa.Uuid, nullable=False),
        sa.Column("amr", sa.String(20), nullable=False),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        *_timestamps(),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_sessions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_sessions_user_id_users"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid, nullable=False),
        sa.Column("session_id", sa.Uuid, nullable=False),
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("family_id", sa.Uuid, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.ForeignKeyConstraint(
            ["session_id"], ["sessions.id"], name="fk_refresh_tokens_session_id_sessions"
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        # Só o SHA-256 em hexadecimal (R3.3): um token em claro não cabe neste formato.
        sa.CheckConstraint(
            "token_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_refresh_tokens_token_hash_sha256")
        ),
    )
    op.create_index("ix_refresh_tokens_session_id", "refresh_tokens", ["session_id"])


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("sessions")
    op.drop_table("users")
