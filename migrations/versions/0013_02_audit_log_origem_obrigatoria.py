"""audit: tipo de ator e resultado obrigatórios nos eventos novos (spec 013, T7; R1.6).

Uma CHECK `NOT VALID`: vale para todo INSERT novo e não confere as linhas anteriores à 013, que
ficam como estão. A constraint nunca é validada (ver o cabeçalho do SQL). SQL em
`migrations/sql/0013_02/`.

Revision ID: 0013_02
Revises: 0013_01
Create Date: 2026-11-11
"""

from collections.abc import Sequence

from alembic import op

from migrations.sql_loader import executar_sql

revision: str = "0013_02"
down_revision: str | Sequence[str] | None = "0013_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVISAO = "0013_02"


def upgrade() -> None:
    executar_sql(REVISAO, "01_ck_audit_log_origem_obrigatoria.sql")


def downgrade() -> None:
    op.execute("ALTER TABLE audit_log DROP CONSTRAINT ck_audit_log_origem_obrigatoria")
