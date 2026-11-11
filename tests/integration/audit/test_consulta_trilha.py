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


# --- Spec 013, T12: origem só com `auditoria:read_acessos` e leitura auditada

AGENTE_SENTINELA = "Sentinela-UA-013-T12"


async def _evento_com_origem(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> tuple[int, Any]:
    """Uma unidade criada com o User-Agent sentinela; devolve o id do evento e a sessão do autor."""
    autor = await logado(sessoes, ("GESTOR_DADOS", GLOBAL))
    corpo = {
        "nome": "CAPS Origem",
        "tipo_unidade_id": await id_pelo_codigo(sessoes, "tipo_unidade", "CAPS_II"),
        "distrito_id": await id_pelo_codigo(sessoes, "distrito", "DS-I"),
        "cep": "50010100",
        "endereco": "Rua B, 2",
        "status": "ativa",
    }
    await cliente.post(
        "/api/v1/unidades",
        json=corpo,
        headers=bearer(app, autor) | {"User-Agent": AGENTE_SENTINELA},
    )
    async with sessoes() as sessao:
        evento = await sessao.scalar(
            text("SELECT id FROM audit_log WHERE user_agent = :ua"), {"ua": AGENTE_SENTINELA}
        )
    return int(evento), autor.id


async def test_detalhe_esconde_origem_sem_read_acessos(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R8.2: o Gestor de Dados (sem `read_acessos`) vê o evento, o hash e o request id, mas
    IP, User-Agent e sessão vêm nulos, com `origem_restrita`."""
    evento, _ = await _evento_com_origem(app, cliente, sessoes)
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))

    resposta = await cliente.get(f"/api/v1/auditoria/eventos/{evento}", headers=gestor)

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert (corpo["ip"], corpo["user_agent"], corpo["sessao_id"]) == (None, None, None)
    assert corpo["origem_restrita"] is True
    assert len(corpo["hash"]) == 64
    assert (corpo["autor"]["tipo"], corpo["origem"], corpo["resultado"]) == (
        "usuario",
        "api",
        "success",
    )
    assert AGENTE_SENTINELA not in resposta.text


async def test_detalhe_mostra_origem_ao_auditor(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R8.2: o Auditor (com `read_acessos`) vê IP, User-Agent e sessão."""
    evento, sessao_do_autor = await _evento_com_origem(app, cliente, sessoes)
    auditor = bearer(app, await logado(sessoes, ("AUDITOR", GLOBAL)))

    corpo = (await cliente.get(f"/api/v1/auditoria/eventos/{evento}", headers=auditor)).json()

    assert (corpo["ip"], corpo["user_agent"]) == ("127.0.0.1", AGENTE_SENTINELA)
    assert corpo["sessao_id"] == str(sessao_do_autor)
    assert corpo["origem_restrita"] is False


async def test_detalhe_grava_evento_consultado(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R7.4: cada detalhe visto grava `auditoria.evento_consultado` com o id do evento e
    nada mais; um evento inexistente (404) não grava."""
    evento, _ = await _evento_com_origem(app, cliente, sessoes)
    auditor_sessao = await logado(sessoes, ("AUDITOR", GLOBAL))
    auditor = bearer(app, auditor_sessao)

    await cliente.get(f"/api/v1/auditoria/eventos/{evento}", headers=auditor)
    inexistente = await cliente.get("/api/v1/auditoria/eventos/999999", headers=auditor)

    assert inexistente.status_code == 404
    async with sessoes() as sessao:
        linhas = (
            await sessao.execute(
                text(
                    "SELECT entity_type, entity_id, metadata, changes, actor_user_id, result"
                    " FROM audit_log WHERE action = 'auditoria.evento_consultado'"
                )
            )
        ).all()
    assert [tuple(linha) for linha in linhas] == [
        ("evento_auditoria", str(evento), {}, [], auditor_sessao.user_id, "success")
    ]


async def test_gestor_nao_ve_evento_consultado(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R7.4: `auditoria.evento_consultado` é evento de acesso: o Gestor de Dados não o vê na
    lista nem no detalhe (404); o Auditor vê."""
    evento, _ = await _evento_com_origem(app, cliente, sessoes)
    auditor = bearer(app, await logado(sessoes, ("AUDITOR", GLOBAL)))
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    await cliente.get(f"/api/v1/auditoria/eventos/{evento}", headers=auditor)
    async with sessoes() as sessao:
        consulta = await sessao.scalar(
            text("SELECT id FROM audit_log WHERE action = 'auditoria.evento_consultado'")
        )

    do_gestor = await cliente.get(
        "/api/v1/auditoria/eventos", params={"acao": "auditoria."}, headers=gestor
    )
    detalhe = await cliente.get(f"/api/v1/auditoria/eventos/{consulta}", headers=gestor)
    do_auditor = await cliente.get(
        "/api/v1/auditoria/eventos", params={"acao": "auditoria.evento"}, headers=auditor
    )

    assert do_gestor.json()["itens"] == []
    assert detalhe.status_code == 404
    assert [e["acao"] for e in do_auditor.json()["itens"]] == ["auditoria.evento_consultado"]


async def test_evento_antigo_vem_com_campos_novos_nulos(banco_vazio: BancoDeTeste) -> None:
    """013/R1.5: um evento gravado antes da 013 sai na lista e no detalhe com tipo, origem,
    resultado e User-Agent nulos, sem erro."""
    from pydantic import SecretStr
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from src.main import create_app
    from tests.factories import make_settings
    from tests.integration.audit.test_audit_chain import _migrar, _registrar_como_antes_da_013

    await _migrar(banco_vazio.url_dono, "0011_09")
    engine = motor(banco_vazio.url_api)
    sessoes_antigas = async_sessionmaker(engine, expire_on_commit=False)
    await _registrar_como_antes_da_013(sessoes_antigas, "unidade.criada")
    await _migrar(banco_vazio.url_dono, "head")
    aplicacao = create_app(make_settings(database_url=SecretStr(banco_vazio.url_api)))
    auditor = bearer(aplicacao, await logado(sessoes_antigas, ("AUDITOR", GLOBAL)))
    transporte = httpx.ASGITransport(app=aplicacao)
    async with httpx.AsyncClient(transport=transporte, base_url="https://teste") as http:
        lista = await http.get(
            "/api/v1/auditoria/eventos", params={"acao": "unidade."}, headers=auditor
        )
        [antigo] = lista.json()["itens"]
        detalhe = await http.get(f"/api/v1/auditoria/eventos/{antigo['id']}", headers=auditor)
    await aplicacao.state.engine.dispose()
    await engine.dispose()

    assert (antigo["autor"]["tipo"], antigo["origem"], antigo["resultado"]) == (None, None, None)
    assert detalhe.status_code == 200
    assert (detalhe.json()["user_agent"], detalhe.json()["resultado_categoria"]) == (None, None)


async def test_sem_auditoria_read_e_403(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """013/R8.5: sem `auditoria:read`, nem lista nem detalhe (Diretoria; Administrador de TI, que
    tem `read_acessos` mas não `auditoria:read`)."""
    evento, _ = await _evento_com_origem(app, cliente, sessoes)
    for papel in ("DIRETORIA", "ADMIN_TI"):
        cabecalho = bearer(app, await logado(sessoes, (papel, GLOBAL)))
        lista = await cliente.get("/api/v1/auditoria/eventos", headers=cabecalho)
        detalhe = await cliente.get(f"/api/v1/auditoria/eventos/{evento}", headers=cabecalho)
        assert (lista.status_code, detalhe.status_code) == (403, 403), papel


# --- Spec 013, T13: histórico de negócio da unidade (vw_unit_history, migração 0013_04)


async def _historico(cliente: httpx.AsyncClient, unidade: str, cabecalho: dict[str, str]) -> Any:
    resposta = await cliente.get(f"/api/v1/unidades/{unidade}/historico", headers=cabecalho)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["itens"]


async def test_historico_da_unidade_mostra_falha_da_unidade(
    cliente: httpx.AsyncClient, cenario: dict[str, Any]
) -> None:
    """013/R8.7: o `operacao.falhou` com a unidade na entidade aparece, com o resultado e a
    categoria e sem dado de origem."""
    url = f"/api/v1/unidades/{cenario['unidade']}"
    await cliente.patch(url, json={"bairro": "Derby"}, headers=cenario["gestor"])  # 428

    [falha, *_] = await _historico(cliente, cenario["unidade"], cenario["gestor"])

    assert falha["acao"] == "operacao.falhou"
    assert (falha["resultado"], falha["resultado_categoria"]) == ("failure", "precondicao")
    assert {"ip", "user_agent", "sessao_id"}.isdisjoint(falha)


async def test_historico_da_unidade_nao_mostra_acesso_negado_nem_auditoria(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, cenario: dict[str, Any]
) -> None:
    """013/R8.7: `acesso.negado`, `auth.*` e `auditoria.*`, mesmo com a unidade na entidade, são
    da trilha geral e não do histórico de negócio."""
    from src.modules.audit.application.registrar import Ator, Entidade, registrar
    from src.modules.audit.infrastructure.repository import SqlAuditStore

    unidade = cenario["unidade"]
    alheia = await logado(
        sessoes, ("GESTOR_UNIDADE", ("unidade", "01928a3b-0000-7000-8000-0000000000ff"))
    )
    negado = await cliente.patch(
        f"/api/v1/unidades/{unidade}",
        json={"bairro": "Derby"},
        headers=bearer(app, alheia) | {"If-Match": '"2"'},
    )
    for acao in ("auth.login", "auditoria.verificada"):
        async with sessoes() as sessao, sessao.begin():
            await registrar(
                SqlAuditStore(sessao),
                acao=acao,
                ator=Ator(tipo="sistema", origem="teste"),
                entidade=Entidade(tipo="unidade", id=unidade),
            )
    async with sessoes() as sessao:
        na_trilha = set(
            await sessao.scalars(
                text("SELECT action FROM audit_log WHERE entity_id = :id"), {"id": unidade}
            )
        )

    acoes = {e["acao"] for e in await _historico(cliente, unidade, cenario["gestor"])}

    assert negado.status_code == 403
    assert {"acesso.negado", "auth.login", "auditoria.verificada"} <= na_trilha
    assert acoes == {"unidade.criada", "unidade.atualizada", "unidade.equipamento_adicionado"}


async def test_historico_traz_resultado_e_origem(
    cliente: httpx.AsyncClient, cenario: dict[str, Any]
) -> None:
    """013/R1.5, R8.4: cada evento do histórico traz tipo de ator, origem e resultado."""
    itens = await _historico(cliente, cenario["unidade"], cenario["gestor"])

    assert itens
    for item in itens:
        assert (item["autor"]["tipo"], item["origem"], item["resultado"]) == (
            "usuario",
            "api",
            "success",
        )
        assert item["resultado_categoria"] is None
