"""db: ajustes de base da consolidação (spec 011, emenda T21 e T22, de 09/11/2026).

Índices das FKs de equipamento e serviço, CHECKs de status e quantidade, `updated_at` mantido por
trigger, DELETE revogado das tabelas de exclusão lógica, EXECUTE revogado de PUBLIC nas funções
de trigger antigas e `dashboard:read` limitado ao escopo de cada papel (decisão D3). Todo o SQL
está em `migrations/sql/0011_09/`, uma instrução por arquivo, com cabeçalho (011/R11.1).

Revision ID: 0011_09
Revises: 0011_08
Create Date: 2026-11-09
"""

from collections.abc import Sequence

from alembic import op

from migrations.sql_loader import executar_sql

revision: str = "0011_09"
down_revision: str | Sequence[str] | None = "0011_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVISAO = "0011_09"

TABELAS_COM_UPDATED_AT = (
    "equipments",
    "services",
    "districts",
    "technical_areas",
    "unit_types",
    "equipment_types",
    "service_types",
)

ARQUIVOS = (
    "01_ix_equipments_unit_id.sql",
    "02_ix_services_equipment_id.sql",
    "03_ck_equipments_status_valido.sql",
    "04_ck_equipments_quantity_positiva.sql",
    "05_ck_services_status_valido.sql",
    "06_fn_trg_set_updated_at.sql",
    "07_fn_trg_set_updated_at_revoke_public.sql",
    *(
        f"{numero:02d}_trg_set_updated_at_{tabela}.sql"
        for numero, tabela in enumerate(TABELAS_COM_UPDATED_AT, start=8)
    ),
    "15_revoke_delete_exclusao_logica.sql",
    "16_revoke_execute_funcoes_trigger_antigas.sql",
    "17_dashboard_read_escopo_por_papel.sql",
)


def upgrade() -> None:
    for arquivo in ARQUIVOS:
        executar_sql(REVISAO, arquivo)


def downgrade() -> None:
    op.execute(
        "UPDATE role_permissions AS rp SET max_scope = 'global'"
        " FROM roles AS r, permissions AS p"
        " WHERE r.id = rp.role_id AND p.id = rp.permission_id AND p.code = 'dashboard:read'"
        " AND r.code IN ('COORD_TECNICO', 'TECNICO_DISTRITAL', 'GESTOR_UNIDADE')"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION audit_log_somente_insercao(), trg_roles_protect_system()"
        " TO PUBLIC"
    )
    op.execute(
        "GRANT DELETE ON health_units, districts, technical_areas, unit_types, equipment_types,"
        " service_types TO sgs_app"
    )
    for tabela in TABELAS_COM_UPDATED_AT:
        op.execute(f"DROP TRIGGER trg_set_updated_at ON {tabela}")
    op.execute("DROP FUNCTION fn_trg_set_updated_at()")
    op.execute("ALTER TABLE services DROP CONSTRAINT ck_services_status_valido")
    op.execute("ALTER TABLE equipments DROP CONSTRAINT ck_equipments_quantity_positiva")
    op.execute("ALTER TABLE equipments DROP CONSTRAINT ck_equipments_status_valido")
    op.execute("DROP INDEX ix_services_equipment_id")
    op.execute("DROP INDEX ix_equipments_unit_id")
