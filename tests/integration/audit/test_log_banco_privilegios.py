# ruff: noqa: S608
# S608: os nomes de tabela que entram nos comandos destes testes vêm do catálogo do banco de teste
# ou de constantes do arquivo, nunca de entrada externa.
"""Log do banco só para leitura pela aplicação; dono e função do log com privilégio mínimo (011/T7).

As escritas são tentadas pelo login da API (membro do `sgs_app`), o que uma credencial vazada da
aplicação conseguiria fazer; o catálogo é consultado pelo dono do banco.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.integration.postgres import LOGIN_DA_API, BancoDeTeste, motor
from tests.integration.registry.cadastro import inserir_unidade

SEM_PRIVILEGIO = "42501"  # SQLSTATE insufficient_privilege

ESCRITAS = {
    "insert": (
        "INSERT INTO {tabela} (table_name, operation, row_id, changed_columns, db_user, via_api,"
        " txid) VALUES ('health_units', 'DELETE', gen_random_uuid(), '{{}}', 'sgs', true, 1)"
    ),
    "update": "UPDATE {tabela} SET via_api = true, db_user = 'sgs_api'",
    "delete": "DELETE FROM {tabela}",
    "truncate": "TRUNCATE {tabela}",
}
# A tabela-mãe e a partição DEFAULT: escrever direto nela também não pode. As mensais, onde os
# registros caem desde a 011/T8, ficam sem privilégio nenhum (test_particoes.py).
TABELAS = ("db_change_log", "db_change_log_default")


async def _registros(banco: BancoDeTeste) -> list[tuple[str, str, bool]]:
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        linhas = await conexao.execute(
            text("SELECT table_name, operation, via_api FROM db_change_log ORDER BY id")
        )
        registros = [tuple(linha) for linha in linhas]
    await engine.dispose()
    return registros


@pytest.mark.parametrize("tabela", TABELAS)
@pytest.mark.parametrize("escrita", ESCRITAS.values(), ids=ESCRITAS.keys())
async def test_login_da_api_nao_escreve_no_log(
    banco: BancoDeTeste, escrita: str, tabela: str
) -> None:
    """011/R7.6: nem incluir, nem alterar, nem apagar, nem truncar registros diretamente."""
    api = motor(banco.url_api)
    async with api.begin() as conexao:
        await inserir_unidade(conexao, "CAPS José Lucena")
    antes = await _registros(banco)

    with pytest.raises(DBAPIError) as erro:
        async with api.begin() as conexao:
            await conexao.execute(text(escrita.format(tabela=tabela)))
    await api.dispose()

    assert getattr(erro.value.orig, "sqlstate", None) == SEM_PRIVILEGIO
    assert await _registros(banco) == antes == [("health_units", "INSERT", True)]


async def test_login_da_api_le_o_log(banco: BancoDeTeste) -> None:
    """011/R7.6: a aplicação lê o log (para a consulta do Auditor, R7.7)."""
    api = motor(banco.url_api)
    async with api.begin() as conexao:
        unidade = await inserir_unidade(conexao, "CAPS José Lucena")
    async with api.connect() as conexao:
        linhas = await conexao.execute(text("SELECT row_id, operation FROM db_change_log"))
        lidos = [tuple(linha) for linha in linhas]
    await api.dispose()

    assert lidos == [(unidade, "INSERT")]


async def test_log_e_funcao_do_trigger_pertencem_ao_papel_dono(banco: BancoDeTeste) -> None:
    """011/R10.2: a função que roda com privilégio do dono (SECURITY DEFINER) e o log que ela
    grava pertencem ao `sgs_owner`, sem login nem superusuário (011/T3).
    """
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        linha = await conexao.execute(
            text(
                "SELECT"
                " (SELECT pg_get_userbyid(relowner) FROM pg_class"
                "  WHERE oid = 'db_change_log'::regclass),"
                " (SELECT pg_get_userbyid(relowner) FROM pg_class"
                "  WHERE oid = 'db_change_log_default'::regclass),"
                " (SELECT pg_get_userbyid(proowner) FROM pg_proc"
                "  WHERE oid = 'trg_registry_change_log()'::regprocedure),"
                " (SELECT prosecdef FROM pg_proc"
                "  WHERE oid = 'trg_registry_change_log()'::regprocedure)"
            )
        )
        dono_do_log, dono_da_particao, dono_da_funcao, definer = linha.one()
    await engine.dispose()

    assert (dono_do_log, dono_da_particao, dono_da_funcao) == ("sgs_owner",) * 3
    assert definer is True


async def test_so_o_trigger_executa_a_funcao_do_log(banco: BancoDeTeste) -> None:
    """011/R10.1: nem PUBLIC nem a aplicação executam a função; o trigger dispara sem isso
    (as escritas do login da API em test_log_banco.py são registradas).
    """
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        linha = await conexao.execute(
            text(
                "SELECT has_function_privilege('public', 'trg_registry_change_log()', 'EXECUTE'),"
                " has_function_privilege('sgs_app', 'trg_registry_change_log()', 'EXECUTE'),"
                " has_function_privilege(:login, 'trg_registry_change_log()', 'EXECUTE')"
            ),
            {"login": LOGIN_DA_API},
        )
        publico, aplicacao, login = linha.one()
    await engine.dispose()

    assert (publico, aplicacao, login) == (False, False, False)


# --- Spec 013, T10: somente inserção na mãe e em cada partição, e ENABLE ALWAYS (0013_03)

TRIGGER_RECUSOU = "somente inserção"
COMO = {
    "superusuario": None,  # quem roda as migrações nos testes
    "dono": "sgs_owner",  # dono do log e das partições
}


async def _particao_do_registro(banco: BancoDeTeste) -> str:
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        nome = await conexao.scalar(
            text("SELECT tableoid::regclass::text FROM db_change_log ORDER BY id DESC LIMIT 1")
        )
    await engine.dispose()
    return str(nome)


async def _com_registros(banco: BancoDeTeste) -> tuple[str, str]:
    """Um registro numa partição mensal (pela API) e outro na DEFAULT (data sem partição)."""
    api = motor(banco.url_api)
    async with api.begin() as conexao:
        await inserir_unidade(conexao, "CAPS José Lucena")
    await api.dispose()
    mensal = await _particao_do_registro(banco)
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        await conexao.execute(
            text(
                "INSERT INTO db_change_log (occurred_at, table_name, operation, row_id,"
                " changed_columns, db_user, via_api, txid) VALUES ('2000-01-15+00',"
                " 'health_units', 'UPDATE', gen_random_uuid(), '{}', current_user, false, 1)"
            )
        )
    await engine.dispose()
    return mensal, "db_change_log_default"


async def _tentar(banco: BancoDeTeste, papel: str | None, *comandos: str) -> str:
    """Executa os comandos numa transação, como o superusuário ou, com `SET ROLE`, como o dono;
    devolve a mensagem do erro (vazia se tudo passou)."""
    engine = motor(banco.url_dono)
    try:
        async with engine.begin() as conexao:
            if papel is not None:
                await conexao.execute(text(f"SET LOCAL ROLE {papel}"))
            for comando in comandos:
                await conexao.execute(text(comando))
    except DBAPIError as erro:
        return str(erro.orig)
    finally:
        await engine.dispose()
    return ""


@pytest.mark.parametrize("papel", COMO.values(), ids=COMO.keys())
async def test_update_e_delete_recusados_pela_mae_e_direto_na_particao(
    banco: BancoDeTeste, papel: str | None
) -> None:
    """013/R6.1: UPDATE e DELETE recusados pela mãe, numa partição mensal e na DEFAULT, até para
    o dono e o superusuário."""
    mensal, padrao = await _com_registros(banco)
    antes = await _registros(banco)

    for tabela in ("db_change_log", mensal, padrao):
        for comando in (f"UPDATE {tabela} SET via_api = NOT via_api", f"DELETE FROM {tabela}"):
            assert TRIGGER_RECUSOU in await _tentar(banco, papel, comando), comando

    assert await _registros(banco) == antes


@pytest.mark.parametrize("papel", COMO.values(), ids=COMO.keys())
async def test_truncate_recusado_na_mae_na_particao_e_na_default(
    banco: BancoDeTeste, papel: str | None
) -> None:
    """013/R6.2: TRUNCATE recusado na mãe, direto numa partição mensal e direto na DEFAULT."""
    mensal, padrao = await _com_registros(banco)
    antes = await _registros(banco)

    for tabela in ("db_change_log", mensal, padrao):
        assert TRIGGER_RECUSOU in await _tentar(banco, papel, f"TRUNCATE {tabela}"), tabela

    assert await _registros(banco) == antes


async def _particao_nova(banco: BancoDeTeste) -> str:
    """Cria, pelo procedimento, a partição do 13º mês à frente (a migração cria até o 12º)."""
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        await conexao.execute(text("CALL sp_ensure_monthly_partitions('db_change_log', 13)"))
        nome = await conexao.scalar(
            text(
                "SELECT 'db_change_log' || to_char(date_trunc('month', now() AT TIME ZONE 'UTC')"
                " + interval '13 months', '\"_y\"YYYY\"m\"MM')"
            )
        )
    await engine.dispose()
    return str(nome)


async def test_particao_nova_nasce_protegida(banco: BancoDeTeste) -> None:
    """013/R6.4: a partição que o procedimento cria já recusa UPDATE, DELETE e TRUNCATE."""
    nova = await _particao_nova(banco)
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        await conexao.execute(
            text(
                "INSERT INTO db_change_log (occurred_at, table_name, operation, row_id,"
                " changed_columns, db_user, via_api, txid) VALUES (date_trunc('month', now()"
                " AT TIME ZONE 'UTC') + interval '13 months 2 days', 'services', 'DELETE',"
                " gen_random_uuid(), '{}', current_user, false, 1)"
            )
        )
    await engine.dispose()
    assert await _particao_do_registro(banco) == nova

    for comando in (f"UPDATE {nova} SET via_api = true", f"DELETE FROM {nova}", f"TRUNCATE {nova}"):
        assert TRIGGER_RECUSOU in await _tentar(banco, None, comando), comando


async def test_trigger_legitimo_continua_gravando(banco: BancoDeTeste) -> None:
    """013/R6.3: o INSERT do `trg_registry_change_log` (SECURITY DEFINER) segue funcionando, pela
    API e fora dela."""
    api = motor(banco.url_api)
    async with api.begin() as conexao:
        unidade = await inserir_unidade(conexao, "CAPS José Lucena")
        await conexao.execute(
            text("UPDATE health_units SET phone = '8133330000' WHERE id = :id"), {"id": unidade}
        )
    await api.dispose()
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        await conexao.execute(
            text("UPDATE health_units SET phone = '8133331111' WHERE id = :id"), {"id": unidade}
        )
    await engine.dispose()

    assert await _registros(banco) == [
        ("health_units", "INSERT", True),
        ("health_units", "UPDATE", True),
        ("health_units", "UPDATE", False),
    ]


async def test_api_so_tem_select_e_nao_faz_detach_drop_nem_replica(banco: BancoDeTeste) -> None:
    """013/R6.5: o login da API lê a mãe e mais nada: sem privilégio nas partições, sem DETACH,
    sem DROP e sem mudar `session_replication_role`."""
    mensal, _ = await _com_registros(banco)
    tentativas = (
        f"UPDATE {mensal} SET via_api = true",
        f"SELECT count(*) FROM {mensal}",
        f"ALTER TABLE db_change_log DETACH PARTITION {mensal}",
        f"DROP TABLE {mensal}",
        "SET session_replication_role = replica",
    )
    api = motor(banco.url_api)
    for comando in tentativas:
        with pytest.raises(DBAPIError) as erro:
            async with api.begin() as conexao:
                await conexao.execute(text(comando))
        assert getattr(erro.value.orig, "sqlstate", None) == SEM_PRIVILEGIO, comando
    async with api.connect() as conexao:
        assert await conexao.scalar(text("SELECT count(*) FROM db_change_log")) == 2
    await api.dispose()


async def test_triggers_estao_enable_always(banco: BancoDeTeste) -> None:
    """013/R6.8: os três grupos com `tgenabled = 'A'`: imutabilidade da trilha, imutabilidade do
    log (mãe, cada partição existente e uma criada agora pelo procedimento) e log do cadastro."""
    nova = await _particao_nova(banco)
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        linhas = await conexao.execute(
            text(
                "SELECT tgrelid::regclass::text, tgname, tgenabled::text FROM pg_trigger"
                " WHERE NOT tgisinternal AND tgname IN ("
                " 'audit_log_bloqueia_update_delete', 'audit_log_bloqueia_truncate',"
                " 'trg_db_change_log_somente_insercao', 'trg_db_change_log_bloqueia_truncate',"
                " 'trg_registry_change_log')"
            )
        )
        estados = {(tabela, nome): estado for tabela, nome, estado in linhas}
        particoes = set(
            await conexao.scalars(
                text(
                    "SELECT inhrelid::regclass::text FROM pg_inherits"
                    " WHERE inhparent = 'db_change_log'::regclass"
                )
            )
        )
    await engine.dispose()

    esperados = {
        ("audit_log", "audit_log_bloqueia_update_delete"),
        ("audit_log", "audit_log_bloqueia_truncate"),
        *(
            ("db_change_log", n)
            for n in ("trg_db_change_log_somente_insercao", "trg_db_change_log_bloqueia_truncate")
        ),
        *((t, "trg_registry_change_log") for t in ("health_units", "equipments", "services")),
        *(
            (p, n)
            for p in particoes
            for n in ("trg_db_change_log_somente_insercao", "trg_db_change_log_bloqueia_truncate")
        ),
    }
    assert nova in particoes
    assert "db_change_log_default" in particoes
    assert len(particoes) == 15  # DEFAULT + mês atual + 12 à frente + a nova
    assert set(estados) == esperados
    assert set(estados.values()) == {"A"}


async def test_replica_nao_contorna_triggers_enable_always(banco: BancoDeTeste) -> None:
    """013/R6.6, R6.8: com `session_replication_role = replica`, o superusuário continua sem
    alterar a trilha e o log, e a escrita no cadastro continua indo para o log."""
    await _com_registros(banco)
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        await conexao.execute(
            text(
                "INSERT INTO audit_log (occurred_at, action, prev_hash, hash, actor_type, result)"
                " VALUES (now(), 'teste.criado', repeat('0', 64), repeat('a', 64), 'sistema',"
                " 'success')"
            )
        )
    await engine.dispose()
    antes = await _registros(banco)

    for comando in (
        "UPDATE audit_log SET action = 'teste.alterado'",
        "UPDATE db_change_log SET via_api = true",
    ):
        erro = await _tentar(banco, None, "SET LOCAL session_replication_role = replica", comando)
        assert "somente inserção" in erro, comando
    assert (
        await _tentar(
            banco,
            None,
            "SET LOCAL session_replication_role = replica",
            "UPDATE health_units SET phone = '8130000000'",
        )
        == ""
    )

    assert await _registros(banco) == [*antes, ("health_units", "UPDATE", False)]


async def test_limite_dono_consegue_detach_drop_e_disable_trigger(banco: BancoDeTeste) -> None:
    """013/R6.6, R6.7 (caracterização do limite): o dono ainda desanexa e apaga partição e desliga
    o trigger com DDL explícita; depois disso, o UPDATE passa. A proteção é contra a aplicação e
    contra o modo `replica`, não contra quem administra o banco."""
    nova = await _particao_nova(banco)
    mensal, _ = await _com_registros(banco)

    assert (
        await _tentar(banco, "sgs_owner", f"ALTER TABLE db_change_log DETACH PARTITION {nova}")
        == ""
    )
    assert await _tentar(banco, "sgs_owner", f"DROP TABLE {nova}") == ""
    desligado = await _tentar(
        banco,
        "sgs_owner",
        f"ALTER TABLE {mensal} DISABLE TRIGGER trg_db_change_log_somente_insercao",
        f"UPDATE {mensal} SET via_api = NOT via_api",
    )

    assert desligado == ""
    engine = motor(banco.url_dono)
    async with engine.connect() as conexao:
        particoes = set(
            await conexao.scalars(
                text(
                    "SELECT inhrelid::regclass::text FROM pg_inherits"
                    " WHERE inhparent = 'db_change_log'::regclass"
                )
            )
        )
    await engine.dispose()
    assert nova not in particoes
