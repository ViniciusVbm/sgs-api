# ruff: noqa: S106, S108, S608
# S106: senha do PostgreSQL descartável deste teste, que só existe durante ele. S108: os arquivos
# ficam no /tmp dos contêineres descartáveis, não no host. S608: os nomes de trigger do catálogo
# são as constantes de TRIGGERS.
"""Ensaio de backup e restauração da trilha (spec 013, T15; R9.4, R9.6, R9.7).

Dois PostgreSQL 17 descartáveis, criados só para este teste (Testcontainers): `origem` e
`destino`, que faz o papel de outro servidor. No `origem`, o banco é migrado até a 0011_09,
recebe eventos no formato anterior à 013, é migrado até o head e recebe eventos novos; a âncora
é gerada pelo mesmo caso de uso da CLI. O backup segue o procedimento de
`docs/operacao/backup-restauracao.md`: `pg_dumpall --roles-only --no-role-passwords` e
`pg_dump -Fc`; no `destino`, os papéis são recriados e o `pg_restore` roda numa transação. A
conferência é a do procedimento: catálogo, cadeia, cabeça e âncora.

Com `SGS_EVIDENCIAS_DIR` definido, o teste grava lá a evidência do ensaio (JSON, sem dump, sem
senha e sem dado pessoal). Rodar com `env -u SGS_TEST_DATABASE_URL uv run pytest -m slow` neste
arquivo.
"""

import hashlib
import io
import json
import os
import tarfile
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from testcontainers.community.postgres import PostgresContainer

from src.modules.access.application.autorizacao import UsuarioAtual
from src.modules.access.domain.authorization import Global
from src.modules.audit.application.consultar import Ancora, gerar_ancora, verificar_cadeia
from src.modules.audit.application.registrar import Ator, registrar
from src.modules.audit.infrastructure.consultas import SqlConsultasDeAuditoria
from src.modules.audit.infrastructure.repository import SqlAuditStore
from tests.integration.audit.test_audit_chain import _migrar, _registrar_como_antes_da_013
from tests.integration.postgres import motor

pytestmark = pytest.mark.slow

IMAGEM = "postgres:17"
BANCO = "sgs_ensaio"
AUDITOR = UsuarioAtual(
    id=UUID(int=0), sessao_id=UUID(int=0), permissoes={"auditoria:read": (Global(),)}
)
TRIGGERS = (
    "audit_log_bloqueia_update_delete",
    "audit_log_bloqueia_truncate",
    "trg_db_change_log_somente_insercao",
    "trg_db_change_log_bloqueia_truncate",
    "trg_registry_change_log",
)

CATALOGO = {
    "constraint_not_valid": (
        "SELECT convalidated FROM pg_constraint WHERE conname = 'ck_audit_log_origem_obrigatoria'"
    ),
    "triggers": (
        "SELECT tgrelid::regclass::text || ':' || tgname || ':' || tgenabled::text"
        " FROM pg_trigger WHERE NOT tgisinternal AND tgname IN ("
        + ", ".join(f"'{t}'" for t in TRIGGERS)
        + ") ORDER BY 1"
    ),
    "funcoes_definer": (
        "SELECT proname || ':' || prosecdef::text || ':'"
        " || coalesce(array_to_string(proconfig, ','), '')"
        " FROM pg_proc WHERE proname IN ('trg_registry_change_log', 'sp_ensure_monthly_partitions',"
        " 'db_change_log_somente_insercao', 'audit_log_somente_insercao') ORDER BY 1"
    ),
    "privilegios_sgs_app": (
        "SELECT t || ':' || p || ':' || has_table_privilege('sgs_app', t, p)::text"
        " FROM unnest(ARRAY['audit_log', 'db_change_log']) AS t,"
        " unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE']) AS p ORDER BY 1"
    ),
    "particoes": (
        "SELECT inhrelid::regclass::text FROM pg_inherits"
        " WHERE inhparent = 'db_change_log'::regclass ORDER BY 1"
    ),
    "alembic": "SELECT version_num FROM alembic_version",
}


def _url(container: PostgresContainer, banco: str) -> str:
    base = container.get_connection_url().replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    return base.rsplit("/", 1)[0] + f"/{banco}"


def _exec(container: PostgresContainer, *comando: str) -> bytes:
    resultado = container.get_wrapped_container().exec_run(list(comando), user="postgres")
    assert resultado.exit_code == 0, resultado.output.decode(errors="replace")
    saida: bytes = resultado.output
    return saida


def _enviar(container: PostgresContainer, nome: str, conteudo: bytes) -> None:
    pacote = io.BytesIO()
    with tarfile.open(fileobj=pacote, mode="w") as tar:
        info = tarfile.TarInfo(name=nome)
        info.size = len(conteudo)
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(conteudo))
    container.get_wrapped_container().put_archive("/tmp", pacote.getvalue())


@pytest.fixture(scope="module")
def servidores() -> Iterator[tuple[PostgresContainer, PostgresContainer]]:
    origem = PostgresContainer(IMAGEM, username="postgres", password="ensaio", dbname="postgres")
    destino = PostgresContainer(IMAGEM, username="postgres", password="ensaio", dbname="postgres")
    origem.start()
    try:
        destino.start()
        try:
            yield origem, destino
        finally:
            destino.stop()
    finally:
        origem.stop()


async def _catalogo(url: str) -> dict[str, Any]:
    engine = motor(url)
    async with engine.connect() as conexao:
        lido = {nome: list(await conexao.scalars(text(sql))) for nome, sql in CATALOGO.items()}
    await engine.dispose()
    return lido


async def _verificar(url: str, ancora: Ancora) -> Any:
    engine = motor(url)
    async with AsyncSession(engine) as sessao:
        resultado = await verificar_cadeia(
            AUDITOR, None, None, consultas=SqlConsultasDeAuditoria(sessao), ancora=ancora
        )
    await engine.dispose()
    return resultado


async def test_restauracao_preserva_cadeia_ancora_e_protecoes(
    servidores: tuple[PostgresContainer, PostgresContainer],
) -> None:
    """013/R9.4: o banco restaurado noutro servidor tem a constraint ainda NOT VALID, as linhas
    antigas íntegras, recusa evento sem tipo ou resultado, a cadeia, a cabeça e a âncora
    conferem, e os triggers, as funções e os privilégios são os da origem."""
    origem, destino = servidores
    inicio = time.monotonic()
    passos: list[dict[str, str]] = []

    def passo(descricao: str) -> None:
        passos.append(
            {"instante": datetime.now(UTC).isoformat(timespec="seconds"), "passo": descricao}
        )

    _exec(origem, "createdb", BANCO)
    url_origem = _url(origem, BANCO)
    await _migrar(url_origem, "0011_09")
    engine = motor(url_origem)
    sessoes = async_sessionmaker(engine, expire_on_commit=False)
    for acao in ("unidade.criada", "unidade.atualizada"):
        await _registrar_como_antes_da_013(sessoes, acao)
    await _migrar(url_origem, "head")
    for numero in range(3):
        async with sessoes() as sessao, sessao.begin():
            await registrar(
                SqlAuditStore(sessao),
                acao="unidade.atualizada",
                ator=Ator(tipo="sistema", origem="ensaio"),
                metadados={"n": numero},
            )
    async with AsyncSession(engine) as sessao:
        verificacao_origem, gerada = await gerar_ancora(
            AUDITOR, consultas=SqlConsultasDeAuditoria(sessao)
        )
    await engine.dispose()
    assert gerada is not None
    assert verificacao_origem.integra is True
    ancora = Ancora(cadeia_id=gerada.cadeia_id, id=gerada.id, hash=gerada.hash)
    catalogo_origem = await _catalogo(url_origem)
    passo("origem migrada (0011_09, eventos antigos, head, eventos novos) e âncora gerada")

    papeis = _exec(origem, "pg_dumpall", "--roles-only", "--no-role-passwords")
    dump = _exec(
        origem, "sh", "-c", f"pg_dump -Fc -d {BANCO} -f /tmp/backup.dump && cat /tmp/backup.dump"
    )
    checksum = hashlib.sha256(dump).hexdigest()
    passo("pg_dumpall --roles-only --no-role-passwords; pg_dump -Fc; sha256sum do arquivo")

    _enviar(destino, "papeis.sql", papeis)
    _enviar(destino, "backup.dump", dump)
    # Os papéis que já existem no servidor novo (o superusuário) dão aviso, não falha.
    _exec(destino, "psql", "-q", "-f", "/tmp/papeis.sql", "-d", "postgres")
    _exec(destino, "createdb", BANCO)
    _exec(
        destino,
        "pg_restore",
        "--exit-on-error",
        "--single-transaction",
        "-d",
        BANCO,
        "/tmp/backup.dump",
    )
    url_destino = _url(destino, BANCO)
    passo("papéis recriados; createdb; pg_restore --exit-on-error --single-transaction")

    catalogo_destino = await _catalogo(url_destino)
    resultado = await _verificar(url_destino, ancora)
    engine = motor(url_destino)
    async with engine.connect() as conexao:
        antigos = (
            await conexao.execute(
                text("SELECT actor_type, result FROM audit_log ORDER BY id LIMIT 2")
            )
        ).all()
        total = await conexao.scalar(text("SELECT count(*) FROM audit_log"))
    with pytest.raises(IntegrityError, match="ck_audit_log_origem_obrigatoria"):
        async with engine.begin() as conexao:
            await conexao.execute(
                text(
                    "INSERT INTO audit_log (occurred_at, action, prev_hash, hash)"
                    " VALUES (now(), 'teste.criado', repeat('1', 64), repeat('2', 64))"
                )
            )
    await engine.dispose()
    duracao = round(time.monotonic() - inicio, 1)
    passo("catálogo conferido; cadeia, cabeça e âncora verificadas; INSERT sem tipo recusado")

    assert catalogo_destino == catalogo_origem
    assert catalogo_destino["constraint_not_valid"] == [False]
    assert all(t.endswith(":A") for t in catalogo_destino["triggers"])
    # A aplicação só insere e lê a trilha e só lê o log do banco (0001; 011/R7.6; 013/R6.5).
    permitidos = {p for p in catalogo_destino["privilegios_sgs_app"] if p.endswith(":true")}
    assert permitidos == {
        "audit_log:INSERT:true",
        "audit_log:SELECT:true",
        "db_change_log:SELECT:true",
    }
    assert [tuple(linha) for linha in antigos] == [(None, None), (None, None)]
    assert total == gerada.total
    assert (
        resultado.integra,
        resultado.cabeca_confere,
        resultado.cadeia_confere,
        resultado.ancora_confere,
    ) == (True, True, True, True)

    pasta = os.environ.get("SGS_EVIDENCIAS_DIR")
    if pasta:
        evidencia = {
            "ensaio": "restauração da trilha em servidor PostgreSQL 17 novo (descartável)",
            "spec": "013/T15 (R9.4, R9.6, R9.7)",
            "data": datetime.now(UTC).date().isoformat(),
            "executado_por": "proprietário do projeto (único responsável; P1, P6)",
            "conferido_por": "o mesmo responsável (sem segregação de funções; risco aceito, P6)",
            "passos": passos,
            "backup": {"formato": "pg_dump -Fc", "sha256": checksum, "bytes": len(dump)},
            "ancora_usada": {
                "versao": gerada.versao,
                "cadeia_id": gerada.cadeia_id,
                "id": gerada.id,
                "hash": gerada.hash,
                "total": gerada.total,
            },
            "verificacao_restaurado": {
                "integra": resultado.integra,
                "verificados": resultado.verificados,
                "cabeca_confere": resultado.cabeca_confere,
                "cadeia_confere": resultado.cadeia_confere,
                "ancora_confere": resultado.ancora_confere,
            },
            "catalogo_restaurado": catalogo_destino,
            "catalogo_igual_ao_da_origem": catalogo_destino == catalogo_origem,
            "insert_sem_tipo_recusado": True,
            "duracao_segundos": duracao,
            "rto_meta_horas": 4,
        }
        destino_arquivo = Path(pasta) / f"ensaio-restauracao-{evidencia['data']}.json"
        destino_arquivo.parent.mkdir(parents=True, exist_ok=True)
        destino_arquivo.write_text(json.dumps(evidencia, ensure_ascii=False, indent=2) + "\n")
