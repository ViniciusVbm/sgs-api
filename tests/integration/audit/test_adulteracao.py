"""Verificação da cadeia contra adulteração e com escritas concorrentes (spec 013, T8).

As adulterações são feitas como o superusuário do contêiner descartável, com os triggers de
imutabilidade desligados só durante o comando (`DISABLE TRIGGER USER`), como faria quem controla
o banco. A verificação vem pela rota (`POST /auditoria/verificar`) ou, nos testes de concorrência,
pelo caso de uso com sessões reais e independentes do PostgreSQL.
"""

from typing import Any, cast
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from src.modules.access.application.autorizacao import UsuarioAtual
from src.modules.access.domain.authorization import Global
from src.modules.audit.application import consultar
from src.modules.audit.application.consultar import ConsultasDeAuditoria, ResultadoDaVerificacao
from src.modules.audit.application.registrar import Ator, registrar
from src.modules.audit.domain.entry import AuditEntry
from src.modules.audit.infrastructure.consultas import SqlConsultasDeAuditoria
from src.modules.audit.infrastructure.repository import SqlAuditStore
from tests.integration.acesso import GLOBAL, Sessoes, bearer, logado
from tests.integration.postgres import BancoDeTeste, motor

VERIFICAR = "/api/v1/auditoria/verificar"
AUDITOR = UsuarioAtual(
    id=UUID(int=1), sessao_id=UUID(int=1), permissoes={"auditoria:read": (Global(),)}
)


async def _gravar(sessoes: Sessoes, acao: str, **campos: Any) -> AuditEntry:
    async with sessoes() as sessao, sessao.begin():
        return await registrar(
            SqlAuditStore(sessao),
            acao=acao,
            ator=Ator(tipo="sistema", origem="teste", user_agent="agente/1.0"),
            **campos,
        )


async def _tres_eventos(sessoes: Sessoes) -> list[int]:
    await _gravar(sessoes, "unidade.criada")
    await _gravar(sessoes, "unidade.atualizada", resultado="failure", categoria="conflito")
    await _gravar(sessoes, "unidade.desativada")
    async with sessoes() as sessao:
        return list(await sessao.scalars(text("SELECT id FROM audit_log ORDER BY id")))


async def _adulterar(banco: BancoDeTeste, sql: str, parametros: dict[str, Any]) -> None:
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        await conexao.execute(text("ALTER TABLE audit_log DISABLE TRIGGER USER"))
        await conexao.execute(text(sql), parametros)
        await conexao.execute(text("ALTER TABLE audit_log ENABLE TRIGGER USER"))
    await engine.dispose()


async def _verificar(
    app: FastAPI,
    cliente: httpx.AsyncClient,
    sessoes: Sessoes,
    ancora: dict[str, Any] | None = None,
) -> dict[str, Any]:
    auditor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    corpo = {} if ancora is None else {"ancora": ancora}
    resposta = await cliente.post(VERIFICAR, json=corpo, headers=auditor)
    assert resposta.status_code == 200, resposta.text
    return dict(resposta.json())


async def test_delete_no_meio(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste
) -> None:
    """013/R5.2: sem o evento do meio, o seguinte tem um `prev_hash` órfão."""
    ids = await _tres_eventos(sessoes)
    await _adulterar(banco, "DELETE FROM audit_log WHERE id = :id", {"id": ids[1]})

    resultado = await _verificar(app, cliente, sessoes)

    assert resultado["integra"] is False
    assert resultado["primeiro_evento_divergente"] == ids[2]
    assert resultado["motivo"] == "prev_hash não é o hash do evento anterior"
    assert resultado["ultimo_id"] == ids[0]


async def test_delete_no_fim(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste
) -> None:
    """013/R5.1, R5.5: a cadeia restante é coerente, mas o fim não bate com a cabeça."""
    ids = await _tres_eventos(sessoes)
    async with sessoes() as sessao:
        penultimo = await sessao.scalar(
            text("SELECT hash FROM audit_log WHERE id = :id"), {"id": ids[1]}
        )
    await _adulterar(banco, "DELETE FROM audit_log WHERE id = :id", {"id": ids[2]})

    resultado = await _verificar(app, cliente, sessoes)

    assert resultado == {
        "integra": False,
        "verificados": 2,
        "primeiro_evento_divergente": None,
        "motivo": "o fim da cadeia não confere com audit_chain_head",
        "ultimo_id": ids[1],
        "hash_final": penultimo,
        "cabeca_confere": False,
        "cadeia_confere": None,
        "ancora_confere": None,
    }


async def test_delete_do_primeiro_evento_e_detectado(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste
) -> None:
    """013/R5.2: sem o primeiro, o novo primeiro não encadeia na gênese."""
    ids = await _tres_eventos(sessoes)
    await _adulterar(banco, "DELETE FROM audit_log WHERE id = :id", {"id": ids[0]})

    resultado = await _verificar(app, cliente, sessoes)

    assert resultado["integra"] is False
    assert resultado["primeiro_evento_divergente"] == ids[1]
    assert resultado["ultimo_id"] is None


async def _confere_adulteracao(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste, sql: str
) -> None:
    """013/R5.2: alterar o hash, os metadados ou qualquer campo novo da 013 (que entra no conteúdo
    canônico) aponta o próprio evento como divergente."""
    ids = await _tres_eventos(sessoes)  # o do meio é a falha (com categoria)
    await _adulterar(banco, sql, {"id": ids[1]})

    resultado = await _verificar(app, cliente, sessoes)

    assert resultado["integra"] is False
    assert resultado["primeiro_evento_divergente"] == ids[1]
    assert resultado["motivo"] == "o conteúdo não confere com o hash gravado"


async def test_update_de_hash(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste
) -> None:
    """013/R5.2"""
    await _confere_adulteracao(
        app,
        cliente,
        sessoes,
        banco,
        "UPDATE audit_log SET hash = repeat('b', 64) WHERE id = :id",
    )


async def test_update_de_metadata(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste
) -> None:
    """013/R5.2"""
    await _confere_adulteracao(
        app,
        cliente,
        sessoes,
        banco,
        "UPDATE audit_log SET metadata = '{\"adulterado\": true}' WHERE id = :id",
    )


async def test_update_de_result_e_actor_type(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste
) -> None:
    """013/R5.2"""
    await _confere_adulteracao(
        app,
        cliente,
        sessoes,
        banco,
        "UPDATE audit_log SET result = 'denied', result_reason = 'autorizacao', actor_type = 'seed'"
        " WHERE id = :id",
    )


async def test_update_de_origin_user_agent_e_result_reason(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste
) -> None:
    """013/R5.2"""
    await _confere_adulteracao(
        app,
        cliente,
        sessoes,
        banco,
        "UPDATE audit_log SET origin = NULL, user_agent = NULL, result_reason = 'precondicao'"
        " WHERE id = :id",
    )


async def test_truncate_bloqueado(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste
) -> None:
    """013/R5.2: com o trigger ligado, nem o dono trunca a trilha; a cadeia segue íntegra."""
    await _tres_eventos(sessoes)
    engine = motor(banco.url_dono)
    with pytest.raises(DBAPIError, match="somente inserção"):
        async with engine.begin() as conexao:
            await conexao.execute(text("TRUNCATE audit_log"))
    await engine.dispose()

    resultado = await _verificar(app, cliente, sessoes)

    assert resultado["integra"] is True
    assert resultado["cabeca_confere"] is True
    assert resultado["verificados"] == 3


class _Espiao:
    """A porta real, numa sessão real; depois do primeiro lote, outra transação grava e confirma
    eventos novos, como uma escrita concorrente durante a verificação."""

    def __init__(self, sessao: Any, sessoes: Sessoes) -> None:
        self._real = SqlConsultasDeAuditoria(sessao)
        self._sessao = sessao
        self._sessoes = sessoes
        self.lotes = 0
        self.transacao: tuple[str, str] | None = None

    async def fixar_foto_consistente(self) -> None:
        await self._real.fixar_foto_consistente()

    async def cabeca_da_cadeia(self) -> str:
        return await self._real.cabeca_da_cadeia()

    async def hash_anterior(self, id_: int) -> str | None:
        return await self._real.hash_anterior(id_)

    async def lote_da_cadeia(self, *args: Any) -> Any:
        lote = await self._real.lote_da_cadeia(*args)
        self.lotes += 1
        if self.lotes == 1:
            nivel = await self._sessao.scalar(text("SHOW transaction_isolation"))
            so_leitura = await self._sessao.scalar(text("SHOW transaction_read_only"))
            self.transacao = (str(nivel), str(so_leitura))
            await _gravar(self._sessoes, "unidade.criada")
            await _gravar(self._sessoes, "unidade.atualizada")
        return lote


async def test_escrita_concorrente_nao_gera_falso_positivo(
    sessoes: Sessoes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """013/R5.11: com eventos confirmados por outra transação no meio da verificação (entre o
    primeiro e o segundo lote), a cabeça e os lotes são lidos na mesma foto: íntegra, cabeça
    confere, e os eventos novos não são contados."""
    for _ in range(5):
        await _gravar(sessoes, "unidade.criada")
    monkeypatch.setattr(consultar, "LOTE", 2)

    async with sessoes() as sessao:
        espiao = _Espiao(sessao, sessoes)
        resultado = await consultar.verificar_cadeia(
            AUDITOR, None, None, consultas=cast(ConsultasDeAuditoria, espiao)
        )

    assert espiao.transacao == ("repeatable read", "on")
    assert espiao.lotes >= 3
    assert (resultado.integra, resultado.cabeca_confere, resultado.verificados) == (True, True, 5)
    async with sessoes() as sessao:
        assert await sessao.scalar(text("SELECT count(*) FROM audit_log")) == 7


async def test_verificacao_seguinte_inclui_os_eventos_concorrentes(
    sessoes: Sessoes, monkeypatch: pytest.MonkeyPatch
) -> None:
    """013/R5.11: os eventos gravados durante uma verificação entram na seguinte, íntegros."""
    for _ in range(3):
        await _gravar(sessoes, "unidade.criada")
    monkeypatch.setattr(consultar, "LOTE", 2)
    async with sessoes() as sessao:
        primeira = await consultar.verificar_cadeia(
            AUDITOR, None, None, consultas=cast(ConsultasDeAuditoria, _Espiao(sessao, sessoes))
        )

    async with sessoes() as sessao:
        seguinte = await consultar.verificar_cadeia(
            AUDITOR, None, None, consultas=SqlConsultasDeAuditoria(sessao)
        )

    assert (primeira.integra, primeira.verificados) == (True, 3)
    assert (seguinte.integra, seguinte.cabeca_confere, seguinte.verificados) == (True, True, 5)
    assert seguinte.ultimo_id is not None
    assert primeira.ultimo_id is not None
    assert seguinte.ultimo_id > primeira.ultimo_id


async def test_verificacao_grava_evento_em_transacao_separada(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R7.3, R5.11: a rota grava `auditoria.verificada` com o resultado, fora da transação de
    leitura (que é READ ONLY: lá o INSERT seria recusado); o evento não conta na própria
    verificação, e a seguinte o encadeia normalmente."""
    await _tres_eventos(sessoes)

    primeira = await _verificar(app, cliente, sessoes)
    segunda = await _verificar(app, cliente, sessoes)

    async with sessoes() as sessao:
        linhas = (
            await sessao.execute(
                text(
                    "SELECT metadata, result, actor_type, origin FROM audit_log"
                    " WHERE action = 'auditoria.verificada' ORDER BY id"
                )
            )
        ).all()
    assert (primeira["integra"], primeira["verificados"], primeira["cabeca_confere"]) == (
        True,
        3,
        True,
    )
    assert (segunda["integra"], segunda["verificados"]) == (True, 4)
    assert len(linhas) == 2
    assert linhas[0].metadata == {
        "integra": True,
        "verificados": 3,
        "ultimo_id": primeira["ultimo_id"],
        "cabeca_confere": True,
        "cadeia_confere": None,
        "ancora_confere": None,
        "primeiro_evento_divergente": None,
    }
    assert (linhas[0].result, linhas[0].actor_type, linhas[0].origin) == (
        "success",
        "usuario",
        "api",
    )


async def test_verificacao_sem_registrar_execucao_nao_grava(sessoes: Sessoes) -> None:
    """013/R5.11 (base da verificação offline da T9): sem `registrar_execucao`, nada é gravado."""
    await _tres_eventos(sessoes)

    async with sessoes() as sessao:
        resultado: ResultadoDaVerificacao = await consultar.verificar_cadeia(
            AUDITOR, None, None, consultas=SqlConsultasDeAuditoria(sessao)
        )

    assert resultado.integra is True
    async with sessoes() as sessao:
        assert await sessao.scalar(text("SELECT count(*) FROM audit_log")) == 3


# --- Spec 013, T9: âncora externa e cadeia_id


async def _ancora(sessoes: Sessoes, id_: int) -> dict[str, Any]:
    """A âncora como a CLI a produz: o hash do primeiro evento e o do evento `id_`."""
    async with sessoes() as sessao:
        primeiro = await sessao.scalar(text("SELECT hash FROM audit_log ORDER BY id LIMIT 1"))
        hash_ = await sessao.scalar(text("SELECT hash FROM audit_log WHERE id = :id"), {"id": id_})
    return {"cadeia_id": primeiro, "id": id_, "hash": hash_}


async def test_delete_no_fim_com_cabeca_ajustada_so_a_ancora_acusa(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste
) -> None:
    """013/R5.3, R5.5, R5.6: quem apaga o último evento e acerta a cabeça engana a verificação
    sem âncora; a âncora guardada antes acusa."""
    ids = await _tres_eventos(sessoes)
    ancora = await _ancora(sessoes, ids[2])
    async with sessoes() as sessao:
        penultimo = await sessao.scalar(
            text("SELECT hash FROM audit_log WHERE id = :id"), {"id": ids[1]}
        )
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        await conexao.execute(text("ALTER TABLE audit_log DISABLE TRIGGER USER"))
        await conexao.execute(text("DELETE FROM audit_log WHERE id = :id"), {"id": ids[2]})
        await conexao.execute(text("ALTER TABLE audit_log ENABLE TRIGGER USER"))
        await conexao.execute(
            text("UPDATE audit_chain_head SET last_hash = :hash"), {"hash": penultimo}
        )
    await engine.dispose()

    sem_ancora = await _verificar(app, cliente, sessoes)
    com_ancora = await _verificar(app, cliente, sessoes, ancora)

    assert (sem_ancora["integra"], sem_ancora["cabeca_confere"]) == (True, True)
    assert com_ancora["integra"] is False
    assert (com_ancora["cadeia_confere"], com_ancora["ancora_confere"]) == (True, False)
    assert com_ancora["motivo"] == "a âncora não confere (o evento ancorado sumiu ou mudou)"


async def test_delete_do_primeiro_evento_muda_a_cadeia(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, banco: BancoDeTeste
) -> None:
    """013/R5.3: sem o primeiro evento, a cadeia deixa de ser a da âncora."""
    ids = await _tres_eventos(sessoes)
    ancora = await _ancora(sessoes, ids[2])
    await _adulterar(banco, "DELETE FROM audit_log WHERE id = :id", {"id": ids[0]})

    resultado = await _verificar(app, cliente, sessoes, ancora)

    assert resultado["integra"] is False
    assert (resultado["cadeia_confere"], resultado["ancora_confere"]) == (False, True)


async def test_ancora_de_outra_cadeia_nao_confere(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R5.3: mesmo id e mesmo hash, mas outro `cadeia_id` (outro banco com o mesmo nome, por
    exemplo): a cadeia não é a da âncora."""
    ids = await _tres_eventos(sessoes)
    ancora = await _ancora(sessoes, ids[2]) | {"cadeia_id": "f" * 64}

    resultado = await _verificar(app, cliente, sessoes, ancora)

    assert resultado["integra"] is False
    assert (resultado["cadeia_confere"], resultado["ancora_confere"]) == (False, True)
    assert resultado["motivo"] == "a cadeia não é a da âncora (o primeiro evento mudou)"


async def test_ancora_inexistente_nao_confere(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R5.3: um id que não existe na cadeia não confere."""
    ids = await _tres_eventos(sessoes)
    ancora = await _ancora(sessoes, ids[2]) | {"id": 999_999}

    resultado = await _verificar(app, cliente, sessoes, ancora)

    assert resultado["integra"] is False
    assert (resultado["cadeia_confere"], resultado["ancora_confere"]) == (True, False)
