"""IP, User-Agent e sessão da trilha só no detalhe e só para quem tem `auditoria:read_acessos`
(spec 013, T12; R8.2, R8.6). O Gestor de Dados não os acha por nenhuma rota GET."""

from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.routing import APIRoute

from tests.architecture.test_rotas_protegidas import _rotas
from tests.integration.acesso import GLOBAL, Sessoes, bearer, logado
from tests.integration.audit.test_consulta_trilha import AGENTE_SENTINELA, _evento_com_origem

CAMPOS_DE_ORIGEM = {"ip", "user_agent", "sessao_id", "request_id"}


async def test_lista_nao_expoe_origem(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R8.6: nem para o Auditor a lista traz dados de origem."""
    await _evento_com_origem(app, cliente, sessoes)
    for papel in ("AUDITOR", "GESTOR_DADOS"):
        cabecalho = bearer(app, await logado(sessoes, (papel, GLOBAL)))
        resposta = await cliente.get("/api/v1/auditoria/eventos", headers=cabecalho)
        assert resposta.status_code == 200
        assert resposta.json()["itens"], papel
        for item in resposta.json()["itens"]:
            assert CAMPOS_DE_ORIGEM.isdisjoint(item), papel
        assert AGENTE_SENTINELA not in resposta.text, papel


def _caminho(rota: str, valores: dict[str, str]) -> str:
    for nome, valor in valores.items():
        rota = rota.replace("{" + nome + "}", valor)
    return rota


async def test_gestor_dados_nao_encontra_sentinela_em_nenhuma_rota_get(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R8.6: todas as rotas GET da API, com os ids do cenário, chamadas pelo Gestor de Dados:
    nenhuma resposta tem o User-Agent sentinela nem a sessão de quem gravou o evento."""
    evento, sessao_do_autor = await _evento_com_origem(app, cliente, sessoes)
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    lista = await cliente.get("/api/v1/unidades", headers=gestor)
    unidade = lista.json()["itens"][0]["id"]
    valores = {
        "id": unidade,
        "id_": str(evento),
        "tipo": "tipos-equipamento",
        "equipamento_id": unidade,
        "servico_id": unidade,
    }
    rotas: list[tuple[str, APIRoute]] = [
        (caminho, rota)
        for caminho, rota in _rotas(app.routes)
        if "GET" in (rota.methods or set()) and caminho.startswith("/api/v1")
    ]
    vistas: dict[str, int] = {}
    vazamentos: list[str] = []
    for caminho, _ in rotas:
        url = _caminho(caminho, valores)
        resposta = await cliente.get(url, headers=gestor)
        vistas[caminho] = resposta.status_code
        if AGENTE_SENTINELA in resposta.text or str(sessao_do_autor) in resposta.text:
            vazamentos.append(caminho)

    assert len(rotas) > 10
    assert vistas["/api/v1/auditoria/eventos/{id_}"] == 200
    assert vistas["/api/v1/auditoria/eventos"] == 200
    assert vistas["/api/v1/unidades/{id}/historico"] == 200
    assert vazamentos == []


async def test_auditor_ve_origem_so_no_detalhe(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R8.2, R8.6: para o Auditor, o sentinela aparece no detalhe e em nenhum outro lugar da
    trilha (lista e histórico da unidade)."""
    evento, _ = await _evento_com_origem(app, cliente, sessoes)
    auditor = bearer(app, await logado(sessoes, ("AUDITOR", GLOBAL)))
    unidade: Any = (await cliente.get("/api/v1/unidades", headers=auditor)).json()["itens"][0]["id"]

    detalhe = await cliente.get(f"/api/v1/auditoria/eventos/{evento}", headers=auditor)
    lista = await cliente.get("/api/v1/auditoria/eventos", headers=auditor)
    historico = await cliente.get(f"/api/v1/unidades/{unidade}/historico", headers=auditor)

    assert AGENTE_SENTINELA in detalhe.text
    assert AGENTE_SENTINELA not in lista.text
    assert AGENTE_SENTINELA not in historico.text
