"""audit: nome da CHECK de audit_chain_head sem a convenção aplicada duas vezes (spec 001).

A 0001 passou o nome completo `ck_audit_chain_head_linha_unica`, e o Alembic aplicou por cima a
convenção do `metadata` (`ck_%(table_name)s_%(constraint_name)s`). O banco ficou com
`ck_audit_chain_head_ck_audit_chain_head_linha_unica`. Daqui em diante, as migrações marcam nomes
completos com `op.f()`.

Revision ID: 0001_1
Revises: 0001
Create Date: 2026-11-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_1"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOME_DUPLICADO = "ck_audit_chain_head_ck_audit_chain_head_linha_unica"
NOME_CERTO = "ck_audit_chain_head_linha_unica"


def upgrade() -> None:
    op.execute(f"ALTER TABLE audit_chain_head RENAME CONSTRAINT {NOME_DUPLICADO} TO {NOME_CERTO}")


def downgrade() -> None:
    op.execute(f"ALTER TABLE audit_chain_head RENAME CONSTRAINT {NOME_CERTO} TO {NOME_DUPLICADO}")
