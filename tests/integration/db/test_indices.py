"""Prova de uso dos índices com volume (011/T9; R1.3, R1.4).

Num banco de teste isolado: 1.000 unidades, ~3.000 serviços e a trilha correspondente (3 eventos
por unidade). Depois de `ANALYZE`, o plano do histórico de uma unidade usa `ix_audit_log_entity`
e o dos serviços de uma unidade usa `ix_services_unit_id`.

A trilha de volume é inserida em SQL, com hashes sintéticos únicos: a cadeia de hash não é o que
se prova aqui (ela tem testes próprios), e o banco é descartado no fim. Com a variável
`SGS_PLANOS_SAIDA`, os planos são gravados no arquivo indicado, para a documentação.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import text

from tests.integration.postgres import BancoDeTeste, motor

pytestmark = pytest.mark.slow

UNIDADES = 1000
SERVICOS_POR_UNIDADE = 3

_VOLUME = (
    """
    INSERT INTO health_units (id, name, district_id, unit_type_id, cep, address, status)
    SELECT gen_random_uuid(), 'Unidade de volume ' || i,
           (SELECT id FROM districts ORDER BY id LIMIT 1 OFFSET (i % 8)),
           (SELECT id FROM unit_types ORDER BY id LIMIT 1 OFFSET (i % 7)),
           '50010100', 'Rua ' || i, 'ativa'
    FROM generate_series(1, :n) AS i
    """,
    """
    INSERT INTO services (id, service_type_id, unit_id, name, in_cnes, status)
    SELECT gen_random_uuid(), (SELECT min(id) FROM service_types), u.id,
           'Serviço ' || s, s % 2 = 0, 'ativo'
    FROM health_units AS u, generate_series(1, :por) AS s
    """,
    """
    INSERT INTO audit_log (occurred_at, action, entity_type, entity_id, prev_hash, hash,
                           actor_type, result)
    SELECT now() - make_interval(mins => e), 'unidade.atualizada', 'unidade', u.id::text,
           encode(sha256(convert_to('p' || u.id || e, 'UTF8')), 'hex'),
           encode(sha256(convert_to('h' || u.id || e, 'UTF8')), 'hex'),
           'sistema', 'success' -- obrigatórios nos eventos novos (013/R1.6)
    FROM health_units AS u, generate_series(1, 3) AS e
    """,
)

_HISTORICO = """
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT audit_id, occurred_at, action FROM vw_unit_history
WHERE unit_id = CAST(:id AS uuid) ORDER BY occurred_at DESC LIMIT 20
"""
_SERVICOS = """
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, name FROM services WHERE unit_id = CAST(:id AS uuid) ORDER BY name
"""


async def test_planos_usam_os_indices_com_volume(banco: BancoDeTeste) -> None:
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        await conexao.execute(text("ALTER TABLE audit_log DISABLE TRIGGER USER"))
        for sql in _VOLUME:
            await conexao.execute(text(sql), {"n": UNIDADES, "por": SERVICOS_POR_UNIDADE})
        await conexao.execute(text("ALTER TABLE audit_log ENABLE TRIGGER USER"))
    async with engine.connect() as conexao:
        await conexao.execute(text("ANALYZE health_units, services, audit_log"))
        alvo = await conexao.scalar(
            text("SELECT id FROM health_units ORDER BY id LIMIT 1 OFFSET 500")
        )
        historico = "\n".join(
            linha[0] for linha in await conexao.execute(text(_HISTORICO), {"id": alvo})
        )
        servicos = "\n".join(
            linha[0] for linha in await conexao.execute(text(_SERVICOS), {"id": alvo})
        )
        volume = (
            await conexao.execute(
                text(
                    "SELECT (SELECT count(*) FROM health_units), (SELECT count(*) FROM services),"
                    " (SELECT count(*) FROM audit_log)"
                )
            )
        ).one()
    await engine.dispose()

    saida = os.environ.get("SGS_PLANOS_SAIDA")
    if saida:
        Path(saida).write_text(  # noqa: ASYNC240 (uma escrita, só com a variável definida)
            f"Volume: {volume[0]} unidades, {volume[1]} serviços, {volume[2]} eventos.\n\n"
            f"-- Histórico de uma unidade (vw_unit_history)\n{historico}\n\n"
            f"-- Serviços de uma unidade\n{servicos}\n",
            encoding="utf-8",
        )

    assert tuple(volume) == (UNIDADES, UNIDADES * SERVICOS_POR_UNIDADE, UNIDADES * 3)
    assert "ix_audit_log_entity" in historico, historico
    assert "ix_services_unit_id" in servicos, servicos
