"""audit: origem, User-Agent e resultado na trilha (spec 013, T1).

Cinco colunas nuláveis em `audit_log` (`actor_type`, `origin`, `user_agent`, `result`,
`result_reason`) e os CHECKs de domínio. Sem obrigatoriedade: ela entra na 0013_02, depois que todo
caminho de gravação preencher os campos (013/T7). As linhas antigas não mudam e mantêm o hash
(013, design § Emenda à spec 001). SQL em `migrations/sql/0013_01/`, uma instrução por arquivo.

Revision ID: 0013_01
Revises: 0011_09
Create Date: 2026-11-11
"""

from collections.abc import Sequence

from alembic import op

from migrations.sql_loader import executar_sql

revision: str = "0013_01"
down_revision: str | Sequence[str] | None = "0011_09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVISAO = "0013_01"

ARQUIVOS = (
    "01_audit_log_colunas_origem_resultado.sql",
    "02_ck_audit_log_actor_type_valido.sql",
    "03_ck_audit_log_result_valido.sql",
    "04_ck_audit_log_result_reason_valido.sql",
    "05_ck_audit_log_usuario_tem_id.sql",
)

CONSTRAINTS = (
    "ck_audit_log_usuario_tem_id",
    "ck_audit_log_result_reason_valido",
    "ck_audit_log_result_valido",
    "ck_audit_log_actor_type_valido",
)
COLUNAS = ("result_reason", "result", "user_agent", "origin", "actor_type")


def upgrade() -> None:
    for arquivo in ARQUIVOS:
        executar_sql(REVISAO, arquivo)


def downgrade() -> None:
    # Só desfaz sem perda enquanto nenhum evento novo tiver gravado esses campos: com eles,
    # apagar as colunas mudaria o conteúdo canônico desses eventos e quebraria a cadeia.
    for nome in CONSTRAINTS:
        op.execute(f"ALTER TABLE audit_log DROP CONSTRAINT {nome}")
    op.execute("ALTER TABLE audit_log " + ", ".join(f"DROP COLUMN {c}" for c in COLUNAS))
