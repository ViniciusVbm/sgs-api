"""Todo `.sql` escrito à mão tem cabeçalho e as consultas do cadastro levam o escopo (011/T20;
R11.1, R11.4, R2.5; ADR-0009)."""

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
CONSULTAS = sorted((RAIZ / "src" / "modules").glob("*/infrastructure/sql/**/*.sql"))
MIGRACOES = sorted((RAIZ / "migrations" / "sql").glob("*/*.sql"))
CAMPOS = ("-- Objetivo:", "-- Justificativa", "-- Uso:", "-- Requisitos:")
FRAGMENTO = ":scope_global OR"

# Consultas do dashboard que leem o cadastro sem o fragmento, e por quê.
SEM_ESCOPO = {
    "district_exists.sql": "lê só a referência (sem escopo)",
    "unit_type_exists.sql": "lê só a referência (sem escopo)",
    "technical_area_exists.sql": "lê só a referência (sem escopo)",
}


@pytest.mark.parametrize("arquivo", CONSULTAS + MIGRACOES, ids=lambda p: str(p.relative_to(RAIZ)))
def test_todo_sql_tem_cabecalho_completo(arquivo: Path) -> None:
    texto = arquivo.read_text(encoding="utf-8")
    faltando = [campo for campo in CAMPOS if campo not in texto]

    assert faltando == []


@pytest.mark.parametrize(
    "arquivo",
    [a for a in CONSULTAS if "/dashboard/" in str(a)],
    ids=lambda p: p.name,
)
def test_consulta_do_dashboard_aplica_o_escopo(arquivo: Path) -> None:
    """011/R2.5: toda consulta do cadastro filtra pelo escopo de leitura do usuário."""
    if arquivo.name in SEM_ESCOPO:
        pytest.skip(SEM_ESCOPO[arquivo.name])
    assert FRAGMENTO in arquivo.read_text(encoding="utf-8")


def test_cabecalho_sem_dois_pontos_colados_a_palavra() -> None:
    """`src/core/sql.py`: `:palavra` no cabeçalho vira parâmetro do SQLAlchemy."""
    import re

    problemas = [
        f"{a.name}:{n}"
        for a in CONSULTAS
        for n, linha in enumerate(a.read_text(encoding="utf-8").splitlines(), 1)
        if linha.startswith("--") and re.search(r"(?<![:\w]):[A-Za-z_]", linha)
    ]

    assert problemas == []
