"""Falhas de negócio auditadas como `operacao.falhou` (spec 013, T6; R4.3 a R4.8)."""

import json
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from src.core.errors import Forbidden, TooManyRequests
from src.core.logging import configure_logging
from tests.integration.acesso import GLOBAL, Sessoes, bearer, id_pelo_codigo, logado

ROTA = "/api/v1/unidades"
SENTINELA = "Sentinela-013-T6-valor-enviado"


async def _corpo(sessoes: Sessoes, **campos: Any) -> dict[str, Any]:
    return {
        "nome": "CAPS Espaço Azul",
        "tipo_unidade_id": await id_pelo_codigo(sessoes, "tipo_unidade", "CAPS_II"),
        "distrito_id": await id_pelo_codigo(sessoes, "distrito", "DS-I"),
        "cep": "50010100",
        "endereco": "Rua do Sol, 150",
        "status": "ativa",
    } | campos


async def _falhas(sessoes: Sessoes) -> list[dict[str, Any]]:
    async with sessoes() as sessao:
        resultado = await sessao.execute(
            text(
                "SELECT actor_type, origin, actor_user_id, ip, user_agent, entity_type,"
                " entity_id, metadata, result, result_reason, changes"
                " FROM audit_log WHERE action = 'operacao.falhou' ORDER BY id"
            )
        )
        return [dict(linha) for linha in resultado.mappings()]


async def _contar(sessoes: Sessoes, sql: str) -> int:
    async with sessoes() as sessao:
        return int(await sessao.scalar(text(sql)) or 0)


async def _gestor(app: FastAPI, sessoes: Sessoes) -> tuple[dict[str, str], Any]:
    sessao_de_login = await logado(sessoes, ("GESTOR_DADOS", GLOBAL))
    return bearer(app, sessao_de_login) | {"User-Agent": "teste-t6"}, sessao_de_login.user_id


async def test_conflito_grava_um_evento_e_desfaz_o_cadastro(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R4.3: o 409 (CNES repetido) grava um `operacao.falhou` com o ator, a origem e o
    contexto da requisição; a unidade recusada não fica no banco."""
    gestor, gestor_id = await _gestor(app, sessoes)
    await cliente.post(ROTA, json=await _corpo(sessoes, cnes="2345678"), headers=gestor)

    resposta = await cliente.post(
        ROTA, json=await _corpo(sessoes, cnes="2345678", nome="Outro CAPS"), headers=gestor
    )

    assert resposta.status_code == 409
    [falha] = await _falhas(sessoes)
    assert (falha["result"], falha["result_reason"]) == ("failure", "conflito")
    assert (falha["actor_type"], falha["origin"], falha["actor_user_id"]) == (
        "usuario",
        "api",
        gestor_id,
    )
    assert (falha["ip"], falha["user_agent"]) == ("127.0.0.1", "teste-t6")
    assert falha["metadata"] == {
        "metodo": "POST",
        "rota": "/api/v1/unidades",
        "status": 409,
        "codigo": "conflito",
        "campos": [],
    }
    assert await _contar(sessoes, "SELECT count(*) FROM health_units") == 1
    assert (
        await _contar(sessoes, "SELECT count(*) FROM audit_log WHERE action = 'unidade.criada'")
        == 1
    )


async def test_precondicao_falhou_e_ausente(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R4.3, R4.4: 428 (sem If-Match) e 412 (versão antiga), com a unidade do caminho na
    entidade; um evento por requisição."""
    gestor, _ = await _gestor(app, sessoes)
    unidade = (await cliente.post(ROTA, json=await _corpo(sessoes), headers=gestor)).json()
    url = f"{ROTA}/{unidade['id']}"
    await cliente.patch(url, json={"bairro": "Derby"}, headers=gestor | {"If-Match": '"1"'})

    sem = await cliente.patch(url, json={"bairro": "Graças"}, headers=gestor)
    antiga = await cliente.patch(
        url, json={"bairro": "Graças"}, headers=gestor | {"If-Match": '"1"'}
    )

    assert (sem.status_code, antiga.status_code) == (428, 412)
    falhas = await _falhas(sessoes)
    assert [(f["metadata"]["codigo"], f["metadata"]["status"]) for f in falhas] == [
        ("precondicao_ausente", 428),
        ("precondicao_falhou", 412),
    ]
    assert {(f["result"], f["result_reason"]) for f in falhas} == {("failure", "precondicao")}
    assert {(f["entity_type"], f["entity_id"]) for f in falhas} == {("unidade", unidade["id"])}
    assert {f["metadata"]["rota"] for f in falhas} == {"/api/v1/unidades/{id}"}


async def test_validacao_de_dominio(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R4.3, R4.4: 422 de regra de domínio (distrito inexistente), com o nome do campo."""
    gestor, _ = await _gestor(app, sessoes)

    resposta = await cliente.post(
        ROTA, json=await _corpo(sessoes, distrito_id=9999), headers=gestor
    )

    assert resposta.status_code == 422
    [falha] = await _falhas(sessoes)
    assert (falha["result"], falha["result_reason"]) == ("failure", "validacao")
    assert falha["metadata"]["codigo"] == "validacao_dominio"
    assert falha["metadata"]["campos"] == ["distrito_id"]


async def test_erro_interno_simulado(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R4.3: erro que não é HTTP nem de aplicação vira `erro_interno`, com status 500, sem
    nome de classe nem mensagem; o cliente recebe o 500 genérico."""
    gestor, _ = await _gestor(app, sessoes)

    def quebrado(_sessao: Any) -> Any:
        raise RuntimeError(f"falha inesperada com {SENTINELA}")

    app.state.repositorio_de_unidades = quebrado

    resposta = await cliente.post(ROTA, json=await _corpo(sessoes), headers=gestor)

    assert resposta.status_code == 500
    [falha] = await _falhas(sessoes)
    assert (falha["result"], falha["result_reason"]) == ("failure", "erro_interno")
    assert falha["metadata"] == {
        "metodo": "POST",
        "rota": "/api/v1/unidades",
        "status": 500,
        "codigo": "erro_interno",
        "campos": [],
    }
    assert SENTINELA not in json.dumps(falha, default=str)
    assert "RuntimeError" not in json.dumps(falha, default=str)


async def test_evento_de_falha_sobrevive_ao_rollback(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R4.3, R4.9: a alteração recusada (422 de domínio no PATCH) é desfeita por inteiro, sem
    `unidade.atualizada`; o `operacao.falhou` fica gravado, com a unidade na entidade."""
    gestor, _ = await _gestor(app, sessoes)
    unidade = (await cliente.post(ROTA, json=await _corpo(sessoes), headers=gestor)).json()

    resposta = await cliente.patch(
        f"{ROTA}/{unidade['id']}",
        json={"bairro": "Derby", "status": "inativa"},
        headers=gestor | {"If-Match": '"1"'},
    )

    assert resposta.status_code == 422
    [falha] = await _falhas(sessoes)
    assert (falha["entity_type"], falha["entity_id"]) == ("unidade", unidade["id"])
    assert falha["metadata"]["campos"] == ["status"]
    async with sessoes() as sessao:
        linha = (
            await sessao.execute(
                text("SELECT version, status, neighborhood FROM health_units WHERE id = :id"),
                {"id": unidade["id"]},
            )
        ).one()
    assert (linha.version, linha.status, linha.neighborhood) == (1, "ativa", None)
    assert (
        await _contar(sessoes, "SELECT count(*) FROM audit_log WHERE action = 'unidade.atualizada'")
        == 0
    )


async def test_metadata_so_tem_chaves_permitidas_e_nenhum_valor_enviado(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R4.4, R4.5: nenhum valor do corpo, nem a mensagem do erro, chega ao registro."""
    gestor, _ = await _gestor(app, sessoes)
    await cliente.post(ROTA, json=await _corpo(sessoes, cnes="2345678"), headers=gestor)

    resposta = await cliente.post(
        ROTA,
        json=await _corpo(sessoes, cnes="2345678", nome=SENTINELA, endereco=SENTINELA),
        headers=gestor,
    )

    assert resposta.status_code == 409
    async with sessoes() as sessao:
        registro = await sessao.scalar(
            text("SELECT to_jsonb(l)::text FROM audit_log AS l WHERE action = 'operacao.falhou'")
        )
    assert registro is not None
    assert SENTINELA not in registro
    assert resposta.json()["detail"] not in registro
    [falha] = await _falhas(sessoes)
    assert set(falha["metadata"]) == {"metodo", "rota", "status", "codigo", "campos"}
    assert falha["changes"] == []


async def test_falha_ao_auditar_nao_esconde_o_erro_original(
    app: FastAPI,
    cliente: httpx.AsyncClient,
    sessoes: Sessoes,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """013/R4.8: se a gravação do `operacao.falhou` falhar, o cliente recebe o mesmo 409 e o log
    técnico só tem rota, status, código e request id."""
    gestor, _ = await _gestor(app, sessoes)
    await cliente.post(ROTA, json=await _corpo(sessoes, cnes="2345678"), headers=gestor)
    referencia = await cliente.post(
        ROTA, json=await _corpo(sessoes, cnes="2345678", nome="Outro"), headers=gestor
    )
    original = app.state.auditoria

    class _TrilhaFora:
        def __init__(self, sessao: Any) -> None:
            self._real = original(sessao)

        async def lock_chain_head(self) -> str:
            raise RuntimeError(f"trilha indisponível {SENTINELA}")

        async def append(self, entry: Any) -> None:  # pragma: no cover - não chega aqui
            await self._real.append(entry)

    app.state.auditoria = _TrilhaFora
    # O log JSON vai para o stdout capturado só se configurado depois do capsys (como em
    # tests/integration/test_erros_do_banco.py).
    configure_logging("INFO")
    capsys.readouterr()

    resposta = await cliente.post(
        ROTA, json=await _corpo(sessoes, cnes="2345678", nome=SENTINELA), headers=gestor
    )

    saida = capsys.readouterr().out
    assert resposta.status_code == referencia.status_code == 409
    assert resposta.headers["content-type"] == "application/problem+json"
    assert {k: v for k, v in resposta.json().items() if k != "request_id"} == {
        k: v for k, v in referencia.json().items() if k != "request_id"
    }
    assert "auditoria_falha_nao_registrada" in saida
    assert SENTINELA not in saida
    assert len(await _falhas(sessoes)) == 1  # só o da requisição de referência


def _levantar(erro: Exception) -> Any:
    def fabrica(_sessao: Any) -> Any:
        raise erro

    return fabrica


@pytest.mark.parametrize(
    "caso", ["401_sem_token", "404_inexistente", "422_schema", "403_comum", "429"]
)
async def test_erros_nao_selecionados_nao_gravam(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, caso: str
) -> None:
    """013/R4.6: 401, 404, 422 de schema, `Forbidden` comum e `TooManyRequests` não geram
    `operacao.falhou`, nem como erro interno; a resposta é a do erro original."""
    gestor, _ = await _gestor(app, sessoes)
    corpo = await _corpo(sessoes)
    if caso == "401_sem_token":
        resposta = await cliente.post(ROTA, json=corpo)
        esperado = 401
    elif caso == "404_inexistente":
        resposta = await cliente.patch(
            f"{ROTA}/01928a3b-0000-7000-8000-00000000dead",
            json={"bairro": "Derby"},
            headers=gestor | {"If-Match": '"1"'},
        )
        esperado = 404
    elif caso == "422_schema":
        resposta = await cliente.post(ROTA, json={"nome": "Só o nome"}, headers=gestor)
        esperado = 422
    else:
        erro = Forbidden("proibido") if caso == "403_comum" else TooManyRequests("devagar")
        app.state.repositorio_de_unidades = _levantar(erro)
        resposta = await cliente.post(ROTA, json=corpo, headers=gestor)
        esperado = 403 if caso == "403_comum" else 429

    assert resposta.status_code == esperado
    assert await _falhas(sessoes) == []


async def test_negacao_nao_gera_operacao_falhou(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R4.7: uma negação dentro do caso de uso (campo estrutural fora do escopo) fica só como
    `acesso.negado`, uma vez."""
    gestor, _ = await _gestor(app, sessoes)
    unidade = (await cliente.post(ROTA, json=await _corpo(sessoes), headers=gestor)).json()
    da_unidade = bearer(app, await logado(sessoes, ("GESTOR_UNIDADE", ("unidade", unidade["id"]))))

    resposta = await cliente.patch(
        f"{ROTA}/{unidade['id']}",
        json={"distrito_id": await id_pelo_codigo(sessoes, "distrito", "DS-IV")},
        headers=da_unidade | {"If-Match": '"1"'},
    )

    assert resposta.status_code == 403
    assert await _falhas(sessoes) == []
    assert (
        await _contar(sessoes, "SELECT count(*) FROM audit_log WHERE action = 'acesso.negado'") == 1
    )


async def test_falha_sem_id_no_caminho_fica_sem_entidade(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R4.4: sem identificador no caminho (`POST /unidades`), nenhuma entidade é inventada,
    nem a partir do corpo."""
    gestor, _ = await _gestor(app, sessoes)

    await cliente.post(ROTA, json=await _corpo(sessoes, distrito_id=9999), headers=gestor)

    [falha] = await _falhas(sessoes)
    assert (falha["entity_type"], falha["entity_id"]) == (None, None)


async def test_falha_da_unidade_aparece_no_historico_da_unidade(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R8.7 (parte da T6): o `operacao.falhou` com a unidade na entidade aparece no histórico
    dela, com o motivo da falha e sem dado de origem."""
    gestor, _ = await _gestor(app, sessoes)
    unidade = (await cliente.post(ROTA, json=await _corpo(sessoes), headers=gestor)).json()
    await cliente.patch(f"{ROTA}/{unidade['id']}", json={"bairro": "Derby"}, headers=gestor)

    historico = await cliente.get(f"{ROTA}/{unidade['id']}/historico", headers=gestor)

    assert historico.status_code == 200
    acoes = [e["acao"] for e in historico.json()["itens"]]
    assert acoes == ["operacao.falhou", "unidade.criada"]
    [falha] = [e for e in historico.json()["itens"] if e["acao"] == "operacao.falhou"]
    assert falha["metadados"]["codigo"] == "precondicao_ausente"
    assert "ip" not in falha
