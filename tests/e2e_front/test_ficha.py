"""Ficha da unidade: dados, versão e atualização mantidas pelo banco, serviços só para leitura,
histórico da view vw_unit_history e aparelhos "em desenvolvimento" (spec 012, T8 parte A:
R6.1, R6.2; R9.1).

Toda asserção compara a tela com a API no mesmo instante. A escrita (criar e alterar uma
unidade, para mostrar o trigger de versão) é de uma unidade criada pelo próprio teste, no
banco descartável do compose do E2E (design § Dados nos E2E da emenda).
"""

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.e2e_front.apoio import api, nova_unidade, requisicao, token

Sessao = Callable[[str], Page]


@pytest.fixture
def gestor(sessao_de: Sessao) -> Iterator[tuple[Page, str]]:
    pagina = sessao_de("GESTOR_DADOS")
    yield pagina, token(pagina)
    pagina.close()


def _abrir(pagina: Page, unidade_id: str, aba: str = "") -> Any:
    caminho = f"/api/v1/unidades/{unidade_id}"
    with pagina.expect_response(lambda r: r.url.endswith(caminho)) as resposta:
        pagina.goto("/#/sem-acesso")
        pagina.goto(f"/#/unidade/{unidade_id}{'/' + aba if aba else ''}")
    return resposta.value


def _referencias(pagina: Page, token_: str, tipo: str) -> dict[int, dict[str, Any]]:
    return {r["id"]: r for r in api(pagina, token_, f"/referencias/{tipo}")}


def test_dados_versao_e_etag_iguais_aos_da_api(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    unidade = api(pagina, token_, "/unidades?tamanho=1")["itens"][0]
    resposta = _abrir(pagina, unidade["id"])
    dados = resposta.json()
    tipos = _referencias(pagina, token_, "tipos-unidade")
    distritos = _referencias(pagina, token_, "distritos")
    expect(pagina.locator("[data-ref=nome-unidade]")).to_have_text(dados["nome"])
    expect(pagina.locator("[data-ref=cnes]")).to_have_text(
        f"CNES {dados['cnes']}" if dados["cnes"] else "Sem CNES"
    )
    expect(pagina.locator("[data-ref=dado-tipo] dd")).to_have_text(
        tipos[dados["tipo_unidade_id"]]["nome"]
    )
    expect(pagina.locator("[data-ref=dado-distrito] dd")).to_have_text(
        distritos[dados["distrito_id"]]["nome"]
    )
    expect(pagina.locator("[data-ref=status]")).to_have_text(
        {"ativa": "Ativa", "inativa": "Inativa", "em_implantacao": "Em implantação"}[
            dados["status"]
        ]
    )
    # Efeito dos triggers: versão (= ETag) e "Atualizado em" mantidos pelo banco
    expect(pagina.locator("[data-ref=versao]")).to_have_text(str(dados["versao"]))
    assert resposta.headers["etag"] == f'"{dados["versao"]}"'
    ficha = pagina.locator("[data-ref=ficha]")
    expect(ficha).to_have_attribute("data-etag", resposta.headers["etag"])
    expect(pagina.locator("[data-ref=atualizado-em]")).to_have_attribute(
        "data-iso", dados["atualizado_em"]
    )
    expect(pagina.locator("[data-ref=origem-versao]")).to_contain_text("trg_health_units_version")


def test_alteracao_sobe_a_versao_e_aparece_no_historico(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)
    _abrir(pagina, unidade["id"])
    expect(pagina.locator("[data-ref=versao]")).to_have_text(str(unidade["versao"]))
    alterada = requisicao(
        pagina,
        token_,
        "PATCH",
        f"/unidades/{unidade['id']}",
        {"telefone": "8132320000"},
        {"If-Match": f'"{unidade["versao"]}"'},
    )
    assert alterada.ok, alterada.text()
    depois = alterada.json()
    assert depois["versao"] == unidade["versao"] + 1  # trg_health_units_version
    assert depois["atualizado_em"] > unidade["atualizado_em"]
    _abrir(pagina, unidade["id"])
    expect(pagina.locator("[data-ref=versao]")).to_have_text(str(depois["versao"]))
    expect(pagina.locator("[data-ref=atualizado-em]")).to_have_attribute(
        "data-iso", depois["atualizado_em"]
    )
    with pagina.expect_response("**/historico?*") as historico:
        pagina.click("[data-aba=historico]")
    eventos = historico.value.json()["itens"]
    assert [e["acao"] for e in eventos] == ["unidade.atualizada", "unidade.criada"]
    primeiro = pagina.locator("[data-ref=historico] > li").first
    expect(primeiro.locator(".what")).to_have_text("Dados alterados")
    expect(primeiro.locator(".changes")).to_contain_text("8132320000")
    expect(pagina.locator("[data-ref=historico] > li").nth(1).locator(".what")).to_have_text(
        "Unidade cadastrada"
    )


def test_historico_da_view_em_ordem_com_filtros_de_periodo_e_autor(
    gestor: tuple[Page, str],
) -> None:
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)  # evento com autor: o Gestor que criou
    pagina.goto("/#/sem-acesso")
    with pagina.expect_response("**/historico?*") as resposta:
        pagina.goto(f"/#/unidade/{unidade['id']}/historico")
    dados = resposta.value.json()
    expect(pagina.locator("[data-ref=historico] > li")).to_have_count(len(dados["itens"]))
    quando = [e["quando"] for e in dados["itens"]]
    assert quando == sorted(quando, reverse=True)  # mais recente primeiro
    expect(pagina.locator("[data-ref=origem-historico]")).to_contain_text("vw_unit_history")

    autor = dados["itens"][0]["autor"]["id"]
    with pagina.expect_response(f"**/historico?*autor={autor}*") as por_autor:
        pagina.locator(f"[data-autor='{autor}']").first.click()
    assert por_autor.value.ok
    expect(pagina.locator("#uh-autor")).to_be_visible()

    pagina.fill("#uh-de", "2020-01-01")
    pagina.fill("#uh-ate", "2020-01-31")
    with pagina.expect_response("**/historico?*") as vazio_:
        pagina.click("#uh button[type=submit]")
    assert "de=" in vazio_.value.url
    assert "ate=" in vazio_.value.url
    assert vazio_.value.json()["total"] == 0
    expect(pagina.locator("#uh-resultado [data-estado=vazio]")).to_contain_text(
        "Nenhuma alteração com estes filtros"
    )


def test_diretoria_nao_ve_a_aba_de_historico(sessao_de: Sessao) -> None:
    pagina = sessao_de("DIRETORIA")
    pedidos: list[str] = []
    pagina.on("request", lambda r: pedidos.append(r.url))
    unidade = api(pagina, token(pagina), "/unidades?tamanho=1")["itens"][0]
    _abrir(pagina, unidade["id"], "historico")
    expect(pagina.locator("[data-ref=nome-unidade]")).to_be_visible()
    expect(pagina.locator("[data-aba=historico]")).to_have_count(0)
    expect(pagina).to_have_url(f"https://localhost:18444/#/unidade/{unidade['id']}")
    assert not any("/api/v1/" in u and "/historico" in u for u in pedidos)


def test_tecnico_distrital_ve_o_historico_so_do_proprio_distrito(sessao_de: Sessao) -> None:
    pagina = sessao_de("TECNICO_DISTRITAL")
    token_ = token(pagina)
    me = api(pagina, token_, "/me")
    proprio = next(e["id"] for e in me["permissoes"]["auditoria:read"] if e["tipo"] == "distrito")
    do_distrito = api(pagina, token_, f"/unidades?distrito={proprio}&tamanho=1")["itens"][0]
    outras = api(pagina, token_, "/unidades?tamanho=100")["itens"]
    de_outro = next(u for u in outras if str(u["distrito_id"]) != str(proprio))
    _abrir(pagina, do_distrito["id"])
    expect(pagina.locator("[data-aba=historico]")).to_have_count(1)
    _abrir(pagina, de_outro["id"])
    expect(pagina.locator("[data-ref=nome-unidade]")).to_have_text(de_outro["nome"])
    expect(pagina.locator("[data-aba=historico]")).to_have_count(0)


def test_servicos_da_api_e_aparelhos_em_desenvolvimento(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    unidades = api(pagina, token_, "/unidades?tamanho=100")["itens"]
    com_servico = next(u for u in unidades if api(pagina, token_, f"/unidades/{u['id']}/servicos"))
    servicos = api(pagina, token_, f"/unidades/{com_servico['id']}/servicos")
    with pagina.expect_response("**/servicos"):
        _abrir(pagina, com_servico["id"], "servicos")
    expect(pagina.locator("[data-servico]")).to_have_count(len(servicos))
    # Os controles de escrita (T10) e quem os vê estão em test_servicos.py.
    pagina.click("[data-aba=equipamentos]")
    expect(pagina.locator("#u-corpo [data-estado=em-desenvolvimento]")).to_be_visible()


def test_id_inexistente_mostra_nao_encontrada(gestor: tuple[Page, str]) -> None:
    pagina, _ = gestor
    resposta = _abrir(pagina, str(uuid.uuid4()))
    assert resposta.status == 404
    expect(pagina.locator("[data-estado=nao-encontrada]")).to_contain_text("Unidade não encontrada")


def test_a_lista_abre_a_ficha(gestor: tuple[Page, str]) -> None:
    pagina, _ = gestor
    pagina.goto("/#/sem-acesso")
    with pagina.expect_response("**/api/v1/unidades?*") as lista:
        pagina.goto("/#/unidades")
    primeira = lista.value.json()["itens"][0]
    pagina.locator(f"tr[data-id='{primeira['id']}']").click()
    expect(pagina.locator("[data-ref=nome-unidade]")).to_have_text(primeira["nome"])


def test_gestor_de_unidade_abre_o_historico_da_propria_unidade(sessao_de: Sessao) -> None:
    pagina = sessao_de("GESTOR_UNIDADE")
    with pagina.expect_response("**/historico?*"):
        pagina.locator(".nav a", has_text="Histórico da unidade").click()
    expect(pagina.locator("[data-aba=historico]")).to_have_class("on")
    expect(pagina.locator("[data-ref=historico] > li").first).to_be_visible()


@pytest.mark.parametrize("largura", [1280, 390])
def test_sem_rolagem_horizontal(gestor: tuple[Page, str], largura: int) -> None:
    pagina, token_ = gestor
    pagina.set_viewport_size({"width": largura, "height": 900})
    unidade = api(pagina, token_, "/unidades?tamanho=1")["itens"][0]
    for aba in ("", "servicos", "historico"):
        _abrir(pagina, unidade["id"], aba)
        conteudo = pagina.locator("#u-corpo dl, #u-corpo ol, #u-corpo .empty, #u-corpo table")
        expect(conteudo.first).to_be_visible()
        assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), aba


def test_historico_mostra_tentativa_sem_sucesso(gestor: tuple[Page, str]) -> None:
    """013/R8.4, R8.7: a tentativa recusada (PATCH sem If-Match, 428) aparece no histórico da
    ficha como "Tentativa sem sucesso", com o chip de falha; as alterações têm o chip de sucesso."""
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)
    recusada = requisicao(
        pagina, token_, "PATCH", f"/unidades/{unidade['id']}", {"bairro": "Derby"}
    )
    assert recusada.status == 428

    with pagina.expect_response("**/historico?*"):
        pagina.goto(f"/#/unidade/{unidade['id']}/historico")

    itens = pagina.locator("[data-ref=historico] > li")
    expect(itens.first.locator(".what")).to_have_text("Tentativa sem sucesso")
    expect(itens.first.locator("[data-ref=resultado]")).to_have_attribute(
        "data-resultado", "failure"
    )
    expect(itens.nth(1).locator("[data-ref=resultado]")).to_have_attribute(
        "data-resultado", "success"
    )
