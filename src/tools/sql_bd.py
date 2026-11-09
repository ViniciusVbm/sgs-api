# ruff: noqa: S608
# S608: este módulo gera um arquivo .sql offline a partir de seeds/demo/*.json, que é do próprio
# repositório; os valores passam por `_texto` (aspas escapadas). Nada é executado com entrada de
# usuário.
"""Arquivo SQL único da disciplina de Banco de Dados (spec 011, T20; R11.3 a R11.5).

    make sql-bd            # ou: uv run python -m src.tools.sql_bd

Gera, em `build/` (fora do Git):
- `sql-bd.sql`: o DDL de todas as migrações, na ordem do Alembic (modo offline, sem conectar),
  seguido de todas as consultas escritas à mão (`src/modules/*/infrastructure/sql/*.sql`), cada
  uma com o seu cabeçalho de objetivo, justificativa, uso e requisito. Instala a estrutura num
  PostgreSQL 17 vazio: `psql -v ON_ERROR_STOP=1 -f build/sql-bd.sql`.
- `sql-bd-insercao.sql`: os dados de demonstração de `seeds/demo/` como INSERTs (Etapa 02:
  script de inserção), com as referências pelo código. Os usuários levam o hash Argon2id da
  senha de `SGS_SEED_SENHA` (ou de uma gerada e mostrada uma vez). Não grava auditoria: para a
  trilha, use `sgs-admin seed demo`, que passa pelos casos de uso.

As consultas vão comentadas como exemplos de uso (os parâmetros `:nome` não rodam no psql); o
DDL roda inteiro.
"""

import io
import json
import os
import secrets
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "build"
SEEDS = RAIZ / "seeds" / "demo"


def ddl() -> str:
    """O DDL das migrações, da base até a última, pelo modo offline do Alembic."""
    saida = io.StringIO()
    config = Config(str(RAIZ / "alembic.ini"), output_buffer=saida)
    config.set_main_option("script_location", str(RAIZ / "migrations"))
    command.upgrade(config, "head", sql=True)
    return saida.getvalue()


def arquivos_de_consulta() -> list[Path]:
    """Os `.sql` escritos à mão dos módulos, em ordem de módulo e nome."""
    return sorted((RAIZ / "src" / "modules").glob("*/infrastructure/sql/**/*.sql"))


def consultas() -> str:
    partes = []
    for arquivo in arquivos_de_consulta():
        relativo = arquivo.relative_to(RAIZ)
        corpo = "\n".join(
            f"-- | {linha}" for linha in arquivo.read_text(encoding="utf-8").splitlines()
        )
        partes.append(f"-- ==== {relativo}\n{corpo}\n")
    return "\n".join(partes)


def sql_unico() -> str:
    return (
        "-- SGS API · arquivo SQL único da disciplina de Banco de Dados (spec 011, T20).\n"
        "-- Gerado por `make sql-bd`. Parte 1 roda inteira num PostgreSQL 17 vazio; a Parte 2\n"
        "-- traz as consultas da aplicação, comentadas (os parâmetros :nome são do SQLAlchemy).\n\n"
        "-- ==================== Parte 1: estrutura (DDL das migrações) ====================\n"
        f"{ddl()}\n"
        "-- ==================== Parte 2: consultas da aplicação ====================\n"
        f"{consultas()}"
    )


def _texto(valor: object) -> str:
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, int):
        return str(valor)
    return "'" + str(valor).replace("'", "''") + "'"


def _linhas(itens: Iterable[str]) -> str:
    return ",\n".join(f"    {item}" for item in itens)


def insercao(senha: str) -> str:
    """INSERTs dos dados de `seeds/demo/`, idempotentes (`ON CONFLICT DO NOTHING`)."""
    from src.modules.identity.infrastructure.passwords import Argon2PasswordHasher

    referencias: dict[str, Any] = json.loads((SEEDS / "referencias.json").read_text("utf-8"))
    unidades: list[dict[str, Any]] = json.loads((SEEDS / "unidades.json").read_text("utf-8"))[
        "unidades"
    ]
    vinculos: dict[str, Any] = json.loads((SEEDS / "vinculos.json").read_text("utf-8"))
    usuarios: list[dict[str, Any]] = json.loads((SEEDS / "usuarios.json").read_text("utf-8"))[
        "usuarios"
    ]
    hash_ = Argon2PasswordHasher().hash(senha)
    partes = [
        "-- SGS API · script de inserção dos dados de demonstração (Etapa 02; spec 010).",
        "-- Gerado por `make sql-bd` a partir de seeds/demo/. Rode depois de build/sql-bd.sql.",
        "-- Referências pelo código; ids de negócio gerados pelo banco (gen_random_uuid()).",
        "BEGIN;",
        "INSERT INTO unit_types (code, name, technical_area_id)\nSELECT v.code, v.name, a.id"  # nosec B608 (ver o comentário do topo)
        " FROM (VALUES\n"
        + _linhas(
            f"({_texto(t['codigo'])}, {_texto(t['nome'])}, {_texto(t['area'])})"
            for t in referencias["tipos_unidade"]
        )
        + "\n) AS v (code, name, area) JOIN technical_areas AS a ON a.code = v.area"
        " ON CONFLICT DO NOTHING;",
        "INSERT INTO equipment_types (code, name) VALUES\n"  # nosec B608 (ver o comentário do topo)
        + _linhas(
            f"({_texto(t['codigo'])}, {_texto(t['nome'])})"
            for t in referencias["tipos_equipamento"]
        )
        + "\nON CONFLICT DO NOTHING;",
        "INSERT INTO health_units (id, name, cnes, unit_type_id, district_id, cep, address,"  # nosec B608 (ver o comentário do topo)
        " neighborhood, phone, status, pending_issues)\n"
        "SELECT gen_random_uuid(), v.name, v.cnes, t.id, d.id, v.cep, v.address, v.bairro,"
        " v.phone, v.status, v.pendencias FROM (VALUES\n"
        + _linhas(
            "("
            + ", ".join(
                _texto(u[c])
                for c in (
                    "nome",
                    "cnes",
                    "tipo",
                    "distrito",
                    "cep",
                    "endereco",
                    "bairro",
                    "telefone",
                    "status",
                    "pendencias",
                )
            )
            + ")"
            for u in unidades
        )
        + "\n) AS v (name, cnes, tipo, distrito, cep, address, bairro, phone, status, pendencias)\n"
        "JOIN unit_types AS t ON t.code = v.tipo JOIN districts AS d ON d.code = v.distrito\n"
        "ON CONFLICT DO NOTHING;",
        "INSERT INTO equipments (id, unit_id, name, equipment_type_code, quantity, status)\n"  # nosec B608 (ver o comentário do topo)
        "SELECT gen_random_uuid(), u.id, v.name, v.tipo, v.quantidade, 'ativo' FROM (VALUES\n"
        + _linhas(
            f"({_texto(e['unidade'])}, {_texto(e['nome'])}, {_texto(e['tipo'])},"
            f" {_texto(e['quantidade'])})"
            for e in vinculos["equipamentos"]
        )
        + "\n) AS v (unidade, name, tipo, quantidade)\n"
        "LEFT JOIN health_units AS u ON u.name = v.unidade;",
        "INSERT INTO services (id, unit_id, equipment_id, service_type_id, name, in_cnes,"  # nosec B608 (ver o comentário do topo)
        " status)\n"
        "SELECT gen_random_uuid(), u.id, e.id, st.id, v.name, v.no_cnes, 'ativo' FROM (VALUES\n"
        + _linhas(
            f"({_texto(s['unidade'])}, {_texto(s.get('equipamento'))}, {_texto(s['tipo'])},"
            f" {_texto(s['nome'])}, {_texto(s['no_cnes'])})"
            for s in vinculos["servicos"]
        )
        + "\n) AS v (unidade, equipamento, tipo, name, no_cnes)\n"
        "JOIN service_types AS st ON st.code = v.tipo\n"
        "LEFT JOIN health_units AS u ON u.name = v.unidade\n"
        "LEFT JOIN equipments AS e ON e.name = v.equipamento AND e.unit_id = u.id;",
        "INSERT INTO users (id, username, display_name, password_hash, source) VALUES\n"  # nosec B608 (ver o comentário do topo)
        + _linhas(
            f"(gen_random_uuid(), {_texto(u['username'])}, {_texto(u['nome'])},"
            f" {_texto(hash_)}, 'local')"
            for u in usuarios
        )
        + "\nON CONFLICT DO NOTHING;",
        "INSERT INTO role_assignments (id, user_id, role_id, scope_type, scope_id, origin)\n"  # nosec B608 (ver o comentário do topo)
        "SELECT gen_random_uuid(), usr.id, r.id, v.escopo_tipo,\n"
        "    CASE v.escopo_tipo\n"
        "        WHEN 'area' THEN (SELECT CAST(id AS text) FROM technical_areas"
        " WHERE code = v.valor)\n"
        "        WHEN 'distrito' THEN (SELECT CAST(id AS text) FROM districts"
        " WHERE code = v.valor)\n"
        "        WHEN 'unidade' THEN (SELECT CAST(id AS text) FROM health_units"
        " WHERE name = v.valor)\n"
        "    END, 'direct'\nFROM (VALUES\n"
        + _linhas(
            f"({_texto(u['username'])}, {_texto(u['papel'])}, {_texto(u['escopo']['tipo'])},"
            f" {_texto(u['escopo']['valor'])})"
            for u in usuarios
        )
        + "\n) AS v (username, papel, escopo_tipo, valor)\n"
        "JOIN users AS usr ON usr.username = v.username JOIN roles AS r ON r.code = v.papel;",
        "COMMIT;",
    ]
    return "\n\n".join(partes) + "\n"


def main() -> int:
    SAIDA.mkdir(exist_ok=True)
    (SAIDA / "sql-bd.sql").write_text(sql_unico(), encoding="utf-8")
    senha = os.environ.get("SGS_SEED_SENHA")
    gerada = senha is None
    if senha is None:
        senha = secrets.token_urlsafe(12)
    insercao_sql = SAIDA / "sql-bd-insercao.sql"
    insercao_sql.write_text(insercao(senha), encoding="utf-8")
    insercao_sql.chmod(0o600)
    sys.stdout.write(f"Gerados {SAIDA / 'sql-bd.sql'} e {insercao_sql}.\n")
    if gerada:
        sys.stdout.write(f"Senha dos usuários demo.* no script de inserção: {senha}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
