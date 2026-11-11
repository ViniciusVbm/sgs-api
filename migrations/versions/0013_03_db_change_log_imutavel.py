"""audit: log do banco somente inserção e triggers ENABLE ALWAYS (spec 013, T10).

`db_change_log` recusa UPDATE, DELETE e TRUNCATE (013/R6.1, R6.2), na mãe e em cada partição,
inclusive a DEFAULT e as que o `sp_ensure_monthly_partitions` criar depois (R6.4). Os triggers de
imutabilidade do log e da trilha (`audit_log`, 0001) e o `trg_registry_change_log` passam a
ENABLE ALWAYS: atuam também com `session_replication_role = replica` (R6.8). Dono e superusuário
ainda podem desligá-los com DDL explícita, desanexar ou apagar partições (R6.6, R6.7).

Revision ID: 0013_03
Revises: 0013_02
Create Date: 2026-11-11
"""

from collections.abc import Sequence

from alembic import op

from migrations.sql_loader import executar_sql

revision: str = "0013_03"
down_revision: str | Sequence[str] | None = "0013_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVISAO = "0013_03"

# Como `sgs_owner`, dono do log, das partições, do procedimento e da função (011/R10.2): só o dono
# põe trigger nas tabelas e substitui o procedimento SECURITY DEFINER.
DO_SGS_OWNER = (
    "01_fn_db_change_log_somente_insercao.sql",
    "02_fn_db_change_log_somente_insercao_revoke_public.sql",
    "03_trg_db_change_log_somente_insercao.sql",
    "04_trg_db_change_log_bloqueia_truncate.sql",
    "05_db_change_log_particoes_existentes.sql",
    "06_db_change_log_enable_always_linha.sql",
    "07_db_change_log_enable_always_truncate.sql",
    "08_sp_ensure_monthly_partitions.sql",
)

# Por quem migra, dono da trilha (0001) e das tabelas do cadastro (0006).
DE_QUEM_MIGRA = (
    "09_audit_log_enable_always_update_delete.sql",
    "10_audit_log_enable_always_truncate.sql",
    "11_trg_registry_change_log_enable_always_health_units.sql",
    "12_trg_registry_change_log_enable_always_equipments.sql",
    "13_trg_registry_change_log_enable_always_services.sql",
)


def upgrade() -> None:
    op.execute("SET LOCAL ROLE sgs_owner")
    for arquivo in DO_SGS_OWNER:
        executar_sql(REVISAO, arquivo)
    op.execute("RESET ROLE")
    for arquivo in DE_QUEM_MIGRA:
        executar_sql(REVISAO, arquivo)


def downgrade() -> None:
    for tabela in ("services", "equipments", "health_units"):
        op.execute(f"ALTER TABLE {tabela} ENABLE TRIGGER trg_registry_change_log")
    op.execute("ALTER TABLE audit_log ENABLE TRIGGER audit_log_bloqueia_truncate")
    op.execute("ALTER TABLE audit_log ENABLE TRIGGER audit_log_bloqueia_update_delete")
    op.execute("SET LOCAL ROLE sgs_owner")
    # O procedimento volta ao corpo da 0011_08; os triggers saem das partições e da mãe.
    op.execute("DROP PROCEDURE sp_ensure_monthly_partitions(regclass, integer)")
    executar_sql("0011_08", "01_sp_ensure_monthly_partitions.sql")
    executar_sql("0011_08", "02_sp_ensure_monthly_partitions_revoke_public.sql")
    op.execute(
        "DO $$ DECLARE p record; BEGIN FOR p IN SELECT inhrelid::regclass AS t FROM pg_inherits"
        " WHERE inhparent = 'db_change_log'::regclass LOOP EXECUTE format("
        "'DROP TRIGGER IF EXISTS trg_db_change_log_bloqueia_truncate ON %s', p.t); END LOOP; END $$"
    )
    op.execute("DROP TRIGGER trg_db_change_log_bloqueia_truncate ON db_change_log")
    op.execute("DROP TRIGGER trg_db_change_log_somente_insercao ON db_change_log")
    op.execute("DROP FUNCTION db_change_log_somente_insercao()")
    op.execute("RESET ROLE")
