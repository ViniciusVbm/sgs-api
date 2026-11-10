"""Consulta da trilha (008/T1 a T4), histórico pela view (011/T14) e log do banco (011/T15)."""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text

from tests.integration.acesso import GLOBAL, Sessoes, bearer, id_pelo_codigo, logado
from tests.integration.postgres import BancoDeTeste, motor


@pytest.fixture
async def cenario(app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes) -> dict[str, Any]:
    sessao_do_gestor = await logado(sessoes, ("GESTOR_DADOS", GLOBAL))
    gestor = bearer(app, sessao_do_gestor)
    corpo = {
        "nome": "CAPS Histórico",
        "tipo_unidade_id": await id_pelo_codigo(sessoes, "tipo_unidade", "CAPS_II"),
        "distrito_id": await id_pelo_codigo(sessoes, "distrito", "DS-I"),
        "cep": "50010100",
        "endereco": "Rua A, 1",
        "status": "ativa",
    }
    unidade = (await cliente.post("/api/v1/unidades", json=corpo, headers=gestor)).json()["id"]
    await cliente.patch(
        f"/api/v1/unidades/{unidade}",
        json={"telefone": "(81) 3355-0000"},
        headers=gestor | {"If-Match": '"1"'},
    )
    await cliente.post(
        f"/api/v1/unidades/{unidade}/equipamentos",
        json={"nome": "Poli", "tipo_codigo": "POLICLINICA"},
        headers=gestor,
    )
    return {"gestor": gestor, "gestor_id": str(sessao_do_gestor.user_id), "unidade": unidade}


async def _acoes(
    cliente: httpx.AsyncClient, url: str, headers: dict[str, str], **filtros: str
) -> list[str]:
    resposta = await cliente.get(url, params=filtros, headers=headers)
    assert resposta.status_code == 200, resposta.text
    return [e["acao"] for e in resposta.json()["itens"]]


async def test_historico_da_unidade_pela_view_com_rotulos_e_papel(
    cliente: httpx.AsyncClient, cenario: dict[str, Any]
) -> None:
    """008/R1.1, R1.2; 011/R4.5: mais recente primeiro, com equipamento, autor e papel."""
    resposta = await cliente.get(
        f"/api/v1/unidades/{cenario['unidade']}/historico", headers=cenario["gestor"]
    )

    assert resposta.status_code == 200, resposta.text
    acoes = [e["acao"] for e in resposta.json()["itens"]]
    assert acoes == ["unidade.equipamento_adicionado", "unidade.atualizada", "unidade.criada"]
    atualizada = resposta.json()["itens"][1]
    assert atualizada["autor"]["papeis"] == ["GESTOR_DADOS"]
    assert atualizada["mudancas"] == [
        {"campo": "phone", "rotulo": "Telefone", "de": None, "para": "(81) 3355-0000"}
    ]
    assert atualizada["quando"].endswith("-03:00")


async def test_historico_filtra_por_campo(
    cliente: httpx.AsyncClient, cenario: dict[str, Any]
) -> None:
    """008/R1.3."""
    resposta = await cliente.get(
        f"/api/v1/unidades/{cenario['unidade']}/historico",
        params={"campo": "phone"},
        headers=cenario["gestor"],
    )

    # A criação grava todos os campos (006/R1.6), inclusive o telefone vazio; o equipamento não.
    assert [e["acao"] for e in resposta.json()["itens"]] == ["unidade.atualizada", "unidade.criada"]


async def test_historico_filtra_por_periodo_com_de_inclusivo_e_ate_exclusivo(
    cliente: httpx.AsyncClient, cenario: dict[str, Any]
) -> None:
    """008/R1.3 (008/T6): os limites são instantes de eventos reais, então cada filtro corta
    exatamente num evento."""
    url = f"/api/v1/unidades/{cenario['unidade']}/historico"
    todos = (await cliente.get(url, headers=cenario["gestor"])).json()["itens"]
    adicionado, atualizada, _criada = (e["quando"] for e in todos)

    assert await _acoes(cliente, url, cenario["gestor"], de=atualizada) == [
        "unidade.equipamento_adicionado",
        "unidade.atualizada",
    ]
    assert await _acoes(cliente, url, cenario["gestor"], ate=atualizada) == ["unidade.criada"]
    assert await _acoes(cliente, url, cenario["gestor"], de=atualizada, ate=adicionado) == [
        "unidade.atualizada"
    ]


async def test_historico_filtra_por_autor(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, cenario: dict[str, Any]
) -> None:
    """008/R1.3 (008/T6): só os eventos do autor pedido."""
    outro = await logado(sessoes, ("GESTOR_DADOS", GLOBAL))
    url = f"/api/v1/unidades/{cenario['unidade']}/historico"
    criado = await cliente.post(
        f"/api/v1/unidades/{cenario['unidade']}/equipamentos",
        json={"nome": "Sala de grupo", "tipo_codigo": "POLICLINICA"},
        headers=bearer(app, outro),
    )
    assert criado.status_code == 201, criado.text

    do_outro = await cliente.get(
        url, params={"autor": str(outro.user_id)}, headers=cenario["gestor"]
    )

    assert [(e["acao"], e["autor"]["id"]) for e in do_outro.json()["itens"]] == [
        ("unidade.equipamento_adicionado", str(outro.user_id))
    ]
    assert await _acoes(cliente, url, cenario["gestor"], autor=cenario["gestor_id"]) == [
        "unidade.equipamento_adicionado",
        "unidade.atualizada",
        "unidade.criada",
    ]


async def test_trilha_geral_filtra_por_periodo_entidade_e_autor(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, cenario: dict[str, Any]
) -> None:
    """008/R2.1 (008/T6): `de`, `ate`, `entidade_tipo`, `entidade_id` e `autor`. Um segundo
    autor grava um item de referência, que é outra entidade."""
    outro = await logado(sessoes, ("GESTOR_DADOS", GLOBAL))
    referencia = await cliente.post(
        "/api/v1/referencias/tipos-servico",
        json={"codigo": "OFICINA_T6", "nome": "Oficina"},
        headers=bearer(app, outro),
    )
    assert referencia.status_code == 201, referencia.text
    url, gestor = "/api/v1/auditoria/eventos", cenario["gestor"]
    da_unidade = ["unidade.equipamento_adicionado", "unidade.atualizada", "unidade.criada"]
    todos = (await cliente.get(url, headers=gestor)).json()["itens"]
    [evento_da_referencia] = [e for e in todos if e["entidade_tipo"] == "referencia"]
    quando = {e["acao"]: e["quando"] for e in todos if e["entidade_tipo"] == "unidade"}

    # Período: `de` inclui, `ate` exclui.
    assert await _acoes(
        cliente,
        url,
        gestor,
        de=quando["unidade.atualizada"],
        ate=quando["unidade.equipamento_adicionado"],
    ) == ["unidade.atualizada"]
    assert await _acoes(cliente, url, gestor, ate=quando["unidade.atualizada"]) == [
        "unidade.criada"
    ]
    # Entidade: por tipo, por id e pelos dois juntos.
    assert await _acoes(cliente, url, gestor, entidade_tipo="unidade") == da_unidade
    assert await _acoes(cliente, url, gestor, entidade_tipo="referencia") == [
        evento_da_referencia["acao"]
    ]
    assert await _acoes(cliente, url, gestor, entidade_id=cenario["unidade"]) == da_unidade
    assert (
        await _acoes(
            cliente, url, gestor, entidade_tipo="referencia", entidade_id=cenario["unidade"]
        )
        == []
    )
    # Autor.
    assert await _acoes(cliente, url, gestor, autor=str(outro.user_id)) == [
        evento_da_referencia["acao"]
    ]
    assert await _acoes(cliente, url, gestor, autor=cenario["gestor_id"]) == da_unidade


async def test_historico_fora_do_escopo_e_403(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, cenario: dict[str, Any]
) -> None:
    """008/R1.4: `auditoria:read` de outro distrito não vê."""
    ds2 = await id_pelo_codigo(sessoes, "distrito", "DS-II")
    distrital = bearer(app, await logado(sessoes, ("TECNICO_DISTRITAL", ("distrito", str(ds2)))))

    resposta = await cliente.get(
        f"/api/v1/unidades/{cenario['unidade']}/historico", headers=distrital
    )

    assert resposta.status_code == 403


async def test_eventos_de_acesso_so_com_a_permissao_de_acessos(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, cenario: dict[str, Any]
) -> None:
    """008/R2.1, R2.2: o 403 de antes gera `acesso.negado`; o Gestor de Dados não o vê, o
    Auditor (com `auditoria:read_acessos`) vê."""
    diretoria = bearer(app, await logado(sessoes, ("DIRETORIA", GLOBAL)))
    await cliente.post("/api/v1/unidades", json={}, headers=diretoria)  # 403 auditado
    auditor = bearer(app, await logado(sessoes, ("AUDITOR", GLOBAL)))

    do_gestor = await cliente.get("/api/v1/auditoria/eventos", headers=cenario["gestor"])
    do_auditor = await cliente.get(
        "/api/v1/auditoria/eventos", params={"acao": "acesso."}, headers=auditor
    )

    assert "acesso.negado" not in {e["acao"] for e in do_gestor.json()["itens"]}
    assert {e["acao"] for e in do_auditor.json()["itens"]} == {"acesso.negado"}


async def test_evento_individual_traz_hash_e_prev_hash(
    cliente: httpx.AsyncClient, cenario: dict[str, Any]
) -> None:
    """008/R3.2."""
    lista = await cliente.get("/api/v1/auditoria/eventos", headers=cenario["gestor"])
    primeiro = lista.json()["itens"][-1]["id"]

    resposta = await cliente.get(f"/api/v1/auditoria/eventos/{primeiro}", headers=cenario["gestor"])

    assert resposta.status_code == 200
    assert resposta.json()["prev_hash"] == "0" * 64
    assert len(resposta.json()["hash"]) == 64


async def test_verificacao_acusa_o_evento_adulterado(
    banco: BancoDeTeste, cliente: httpx.AsyncClient, cenario: dict[str, Any]
) -> None:
    """008/R3.1: íntegra antes; depois de o superusuário mudar um registro (com o trigger de
    imutabilidade desligado), aponta o evento exato."""
    antes = await cliente.post("/api/v1/auditoria/verificar", json={}, headers=cenario["gestor"])
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        alvo = await conexao.scalar(
            text("SELECT id FROM audit_log WHERE action = 'unidade.atualizada'")
        )
        await conexao.execute(text("ALTER TABLE audit_log DISABLE TRIGGER USER"))
        await conexao.execute(
            text("UPDATE audit_log SET metadata = '{\"adulterado\": true}' WHERE id = :id"),
            {"id": alvo},
        )
        await conexao.execute(text("ALTER TABLE audit_log ENABLE TRIGGER USER"))
    await engine.dispose()

    depois = await cliente.post("/api/v1/auditoria/verificar", json={}, headers=cenario["gestor"])

    assert antes.json()["integra"] is True
    assert antes.json()["verificados"] >= 3
    assert depois.json()["integra"] is False
    assert depois.json()["primeiro_evento_divergente"] == alvo


async def test_log_do_banco_mostra_alteracao_fora_da_api(
    banco: BancoDeTeste, cliente: httpx.AsyncClient, cenario: dict[str, Any]
) -> None:
    """011/R7.7, T15: o UPDATE do superusuário aparece com `pela_api` falso."""
    engine = motor(banco.url_dono)
    async with engine.begin() as conexao:
        await conexao.execute(
            text("UPDATE health_units SET neighborhood = 'Derby' WHERE id = :id"),
            {"id": cenario["unidade"]},
        )
    await engine.dispose()

    fora = await cliente.get(
        "/api/v1/auditoria/banco", params={"fora_da_api": True}, headers=cenario["gestor"]
    )
    todos = await cliente.get("/api/v1/auditoria/banco", headers=cenario["gestor"])
    particoes = await cliente.get("/api/v1/auditoria/banco/particoes", headers=cenario["gestor"])

    [registro] = fora.json()["itens"]
    assert registro["tabela"] == "health_units"
    assert registro["pela_api"] is False
    assert todos.json()["total"] >= 4
    assert len(particoes.json()) >= 12
    assert sum(p["linhas"] for p in particoes.json()) == todos.json()["total"]


async def test_trilha_geral_exige_escopo_global(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """008/R2.1: `auditoria:read` só de área não lê a trilha geral nem o log do banco."""
    area = await id_pelo_codigo(sessoes, "area", "SAUDE_MENTAL")
    coordenador = bearer(app, await logado(sessoes, ("COORD_TECNICO", ("area", str(area)))))

    eventos = await cliente.get("/api/v1/auditoria/eventos", headers=coordenador)
    log = await cliente.get("/api/v1/auditoria/banco", headers=coordenador)

    assert eventos.status_code == 403
    assert log.status_code == 403
