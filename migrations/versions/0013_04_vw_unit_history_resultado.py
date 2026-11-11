"""db: histórico da unidade com origem e resultado, sem eventos de acesso (spec 013, T13).

Recria `vw_unit_history` (011/T4) com `actor_type`, `origin`, `result` e `result_reason` no fim
e sem `auth.*`, `acesso.negado` e `auditoria.*` (013/R8.7). SQL em `migrations/sql/0013_04/`.

Revision ID: 0013_04
Revises: 0013_03
Create Date: 2026-11-11
"""

from collections.abc import Sequence

from alembic import op

from migrations.sql_loader import executar_sql

revision: str = "0013_04"
down_revision: str | Sequence[str] | None = "0013_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVISAO = "0013_04"


def upgrade() -> None:
    executar_sql(REVISAO, "01_vw_unit_history_resultado.sql")


def downgrade() -> None:
    # CREATE OR REPLACE não tira colunas: a view volta à definição e aos privilégios da 0011_04.
    op.execute("DROP VIEW vw_unit_history")
    executar_sql("0011_04", "02_vw_unit_history.sql")
    executar_sql("0011_04", "03_views_revoke_dml_sgs_app.sql")
