"""`make sql-bd` (011/T20): o arquivo SQL único instala a estrutura num banco vazio e o script de
inserção carrega 30 linhas ou mais nas tabelas de negócio."""

from alembic.script import ScriptDirectory
from sqlalchemy import text

from src.core.db import alembic_config
from src.tools.sql_bd import arquivos_de_consulta, insercao, sql_unico
from tests.integration.postgres import BancoDeTeste, motor

OBJETOS = {
    "views": ("SELECT count(*) FROM pg_views WHERE viewname LIKE 'vw\\_unit\\_%'", 2),
    "procedures": (
        "SELECT count(*) FROM pg_proc WHERE prokind = 'p' AND proname LIKE 'sp\\_%'",
        2,
    ),
    "funções de domínio": (
        "SELECT count(*) FROM pg_proc"
        " WHERE proname IN ('fn_normalize_name', 'fn_registration_status')",
        2,
    ),
    "triggers": (
        "SELECT count(DISTINCT tgname) FROM pg_trigger WHERE NOT tgisinternal"
        " AND tgname IN ('trg_health_units_version', 'trg_registry_change_log')",
        2,
    ),
}


async def _executar(url: str, script: str) -> None:
    engine = motor(url)
    async with engine.connect() as conexao:
        bruta = await conexao.get_raw_connection()
        assert bruta.driver_connection is not None
        await bruta.driver_connection.execute(script)
    await engine.dispose()


async def test_sql_unico_instala_tudo_num_banco_vazio(banco_vazio: BancoDeTeste) -> None:
    """011/R11.3: DDL na ordem das migrações; as consultas vão junto, com cabeçalho."""
    script = sql_unico()

    await _executar(banco_vazio.url_dono, script)
    await _executar(banco_vazio.url_dono, insercao("senha-demo-123"))
    engine = motor(banco_vazio.url_dono)
    async with engine.connect() as conexao:
        objetos = {nome: int(await conexao.scalar(text(sql))) for nome, (sql, _) in OBJETOS.items()}
        contagens = {
            tabela: int(await conexao.scalar(text(f"SELECT count(*) FROM {tabela}")))  # noqa: S608
            for tabela in ("health_units", "equipments", "services", "users", "role_assignments")
        }
        versao = await conexao.scalar(text("SELECT version_num FROM alembic_version"))
    await engine.dispose()

    assert objetos == {nome: minimo for nome, (_, minimo) in OBJETOS.items()}
    assert all(quantidade >= 30 for quantidade in contagens.values()), contagens
    # O head do Alembic, e não uma revisão fixa: cada migração nova entra no SQL único (011/R11.3).
    assert versao == ScriptDirectory.from_config(alembic_config()).get_current_head()
    for arquivo in arquivos_de_consulta():
        assert arquivo.name in script
