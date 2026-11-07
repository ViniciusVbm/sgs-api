"""Tabelas declaradas no código e migrações não divergem.

Se divergirem, `make migrate` (autogenerate) proporia mudanças indevidas, até apagar tabelas.
"""

from typing import Any

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import CheckConstraint, Connection, text

from src.core.db import metadata
from src.modules.access.infrastructure import tables as _access  # noqa: F401 - registra as tabelas
from src.modules.audit.infrastructure import tables as _audit  # noqa: F401
from src.modules.identity.infrastructure import tables as _identity  # noqa: F401
from src.modules.registry.infrastructure import tables as _registry  # noqa: F401
from tests.integration.postgres import BancoDeTeste, motor


def _diferencas(conexao: Connection) -> list[Any]:
    contexto = MigrationContext.configure(conexao, opts={"compare_type": True})
    return list(compare_metadata(contexto, metadata))


async def test_migracoes_e_tabelas_do_codigo_nao_divergem(banco: BancoDeTeste) -> None:
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        diferencas = await conexao.run_sync(_diferencas)
    await engine.dispose()

    assert diferencas == []


async def test_checks_do_banco_tem_os_nomes_do_codigo(banco: BancoDeTeste) -> None:
    """001/R5.2 e 002/T2: o autogenerate não compara CHECKs, então este teste compara os nomes.

    Pega, por exemplo, a convenção de nomes aplicada duas vezes (`ck_users_ck_users_...`).
    """
    no_codigo = {
        (tabela.name, str(restricao.name))
        for tabela in metadata.tables.values()
        for restricao in tabela.constraints
        if isinstance(restricao, CheckConstraint)
    }
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        linhas = await conexao.execute(
            text(
                "SELECT conrelid::regclass::text, conname FROM pg_constraint"
                " WHERE contype = 'c' AND connamespace = 'public'::regnamespace"
            )
        )
        no_banco = {(str(tabela), str(nome)) for tabela, nome in linhas}
    await engine.dispose()

    assert no_banco == no_codigo
