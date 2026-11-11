"""Cadastro e edição de unidades pelo escopo global (spec 012, T9: R7.1 a R7.4).

Cadastro em #/nova (POST /unidades, ficha nova na aba de serviços); edição na ficha com diff de
confirmação e PATCH só dos campos alterados, com If-Match. A API é a autoridade: 422 nos campos,
409 com a unidade existente, 412 quando a ficha mudou em outra sessão. Os dados são criados pelo
próprio teste no banco descartável do compose do E2E.
"""

import secrets
import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from playwright.sync_api import Browser, Page, expect

from tests.e2e_front.apoio import api, nova_unidade, requisicao, token
from tests.e2e_front.conftest import USUARIOS, Autenticador, entrar, novo_contexto

Sessao = Callable[[str], Page]


@pytest.fixture
def gestor(sessao_de: Sessao) -> Iterator[tuple[Page, str]]:
    pagina = sessao_de("GESTOR_DADOS")
    yield pagina, token(pagina)
    pagina.close()


def _abrir(pagina: Page, unidade_id: str) -> Any:
    caminho = f"/api/v1/unidades/{unidade_id}"
    with pagina.expect_response(lambda r: r.url.endswith(caminho)) as resposta:
        pagina.goto("/#/sem-acesso")
        pagina.goto(f"/#/unidade/{unidade_id}")
    expect(pagina.locator("[data-ref=nome-unidade]")).to_be_visible()
    return resposta.value


def _abrir_cadastro(pagina: Page) -> None:
    pagina.goto("/#/sem-acesso")
    pagina.goto("/#/nova")
    expect(pagina.locator("#fn")).to_be_visible()


def _referencias(pagina: Page, token_: str) -> tuple[dict[str, Any], dict[str, Any]]:
    tipo = next(t for t in api(pagina, token_, "/referencias/tipos-unidade") if t["ativo"])
    distrito = api(pagina, token_, "/referencias/distritos")[0]
    return tipo, distrito


def _editar(pagina: Page, valores: dict[str, str]) -> None:
    pagina.click("[data-ref=editar]")
    expect(pagina.locator("#fe")).to_be_visible()
    for campo_, valor in valores.items():
        pagina.fill(f"#fld-{campo_}", valor)
    pagina.click("#fe-enviar")  # revisar: mostra o diff


def test_cadastro_valido_pela_lista_abre_a_ficha_nova(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    tipo, distrito = _referencias(pagina, token_)
    pagina.goto("/#/sem-acesso")
    pagina.goto("/#/unidades")
    pagina.click(".page-head a[href='#/nova']")
    expect(pagina.locator("#fn")).to_be_visible()
    nome = f"USF de teste do cadastro {secrets.token_hex(3)}"
    pagina.fill("#fld-nome", nome)
    pagina.select_option("#fld-tipo_unidade_id", str(tipo["id"]))
    pagina.select_option("#fld-distrito_id", str(distrito["id"]))
    pagina.fill("#fld-endereco", "Rua do Teste, 100")
    pagina.fill("#fld-cep", "50030-230")
    pagina.fill("#fld-bairro", "Boa Vista")
    pagina.fill("#fld-telefone", "8133334444")
    pagina.fill("#fld-latitude", "-8.063169")
    pagina.fill("#fld-longitude", "-34.871139")
    with pagina.expect_response(lambda r: r.request.method == "POST") as resposta:
        pagina.click("#fn button[type=submit]")
    assert resposta.value.status == 201
    corpo: dict[str, Any] = resposta.value.request.post_data_json or {}
    assert corpo["nome"] == nome
    assert corpo["latitude"] == "-8.063169"  # texto: a API (Decimal) recebe o que foi digitado
    assert corpo["cnes"] is None  # opcional vazio vai como nulo
    criada = resposta.value.json()
    assert criada["versao"] == 1
    # A ficha nova abre na aba de serviços (R7.3)
    expect(pagina).to_have_url(f"https://localhost:18444/#/unidade/{criada['id']}/servicos")
    expect(pagina.locator("[data-ref=nome-unidade]")).to_have_text(nome)
    expect(pagina.locator("[data-aba=servicos]")).to_have_class("on")
    gravada = api(pagina, token_, f"/unidades/{criada['id']}")
    assert (gravada["cep"], gravada["bairro"], gravada["telefone"]) == (
        "50030230",
        "Boa Vista",
        "8133334444",
    )
    # Volta à lista e encontra a unidade pela busca
    pagina.click("a.crumb")
    with pagina.expect_response("**/api/v1/unidades?*q=*"):
        pagina.fill("#q", nome)
    expect(pagina.locator(f"tr[data-id='{criada['id']}']")).to_be_visible()


def test_obrigatorios_em_branco_nao_enviam(gestor: tuple[Page, str]) -> None:
    pagina, _ = gestor
    posts: list[str] = []
    pagina.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
    _abrir_cadastro(pagina)
    pagina.click("#fn button[type=submit]")
    for campo_ in ("nome", "tipo_unidade_id", "distrito_id", "endereco", "cep"):
        expect(pagina.locator(f"[data-campo={campo_}] .fld-err")).to_have_text("Campo obrigatório.")
    expect(pagina.locator("[data-campo=bairro] .fld-err")).to_have_text("")  # opcional
    assert posts == []


def test_dados_invalidos_mostram_os_erros_da_api_nos_campos(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    tipo, distrito = _referencias(pagina, token_)
    _abrir_cadastro(pagina)
    pagina.fill("#fld-nome", "Unidade com dados inválidos")
    pagina.select_option("#fld-tipo_unidade_id", str(tipo["id"]))
    pagina.select_option("#fld-distrito_id", str(distrito["id"]))
    pagina.fill("#fld-endereco", "Rua X, 1")
    pagina.fill("#fld-cep", "500")
    pagina.fill("#fld-cnes", "123")
    pagina.fill("#fld-telefone", "abc!")
    pagina.fill("#fld-latitude", "95")
    with pagina.expect_response(lambda r: r.request.method == "POST") as resposta:
        pagina.click("#fn button[type=submit]")
    assert resposta.value.status == 422
    erros = {e["campo"]: e["mensagem"] for e in resposta.value.json()["errors"]}
    assert {"cep", "cnes", "telefone", "latitude"} <= set(erros)
    for campo_ in ("cep", "cnes", "telefone", "latitude"):
        expect(pagina.locator(f"[data-campo={campo_}] .fld-err")).to_have_text(erros[campo_])
    expect(pagina).to_have_url("https://localhost:18444/#/nova")


def test_unidade_repetida_oferece_o_link_da_existente(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    existente = nova_unidade(pagina, token_)
    _abrir_cadastro(pagina)
    pagina.fill("#fld-nome", existente["nome"])
    pagina.select_option("#fld-tipo_unidade_id", str(existente["tipo_unidade_id"]))
    pagina.select_option("#fld-distrito_id", str(existente["distrito_id"]))
    pagina.fill("#fld-endereco", "Outro endereço, 2")
    pagina.fill("#fld-cep", "50000-000")
    with pagina.expect_response(lambda r: r.request.method == "POST") as resposta:
        pagina.click("#fn button[type=submit]")
    assert resposta.value.status == 409
    assert resposta.value.json()["unidade_existente_id"] == existente["id"]
    link = pagina.locator("[data-ref=unidade-existente]")
    expect(link).to_have_attribute("href", f"#/unidade/{existente['id']}")


def test_edicao_com_diff_if_match_versao_e_updated_at(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)
    time.sleep(1.2)  # para a mudança de "Atualizado em" aparecer também nos segundos
    lida = _abrir(pagina, unidade["id"])
    etag = lida.headers["etag"]
    expect(pagina.locator("[data-ref=ficha]")).to_have_attribute("data-etag", etag)

    # Sem mudança: nada é enviado
    patches: list[str] = []
    pagina.on("request", lambda r: patches.append(r.url) if r.method == "PATCH" else None)
    pagina.click("[data-ref=editar]")
    pagina.click("#fe-enviar")
    expect(pagina.locator("#fe")).to_have_count(0)
    assert patches == []

    _editar(pagina, {"telefone": "8131310000", "bairro": "Casa Amarela"})
    diff = pagina.locator("[data-ref=diff]")
    expect(diff.locator("tr[data-campo-diff]")).to_have_count(2)
    expect(diff.locator("tr[data-campo-diff=telefone] .to")).to_have_text("8131310000")
    expect(diff.locator("tr[data-campo-diff=bairro] .from")).to_have_text("—")
    with pagina.expect_response(lambda r: r.request.method == "PATCH") as resposta:
        pagina.click("#fe-enviar")  # confirmar
    pedido = resposta.value.request
    assert pedido.headers["if-match"] == etag  # a versão lida
    assert pedido.post_data_json == {"telefone": "8131310000", "bairro": "Casa Amarela"}
    assert resposta.value.status == 200
    depois = resposta.value.json()
    assert depois["versao"] == unidade["versao"] + 1  # trg_health_units_version
    assert depois["atualizado_em"] > unidade["atualizado_em"]  # gravado pelo mesmo trigger
    assert resposta.value.headers["etag"] == f'"{depois["versao"]}"'

    aviso = pagina.locator("[data-ref=aviso-edicao]")
    expect(aviso).to_have_attribute("data-tipo", "editada")
    expect(aviso).to_have_attribute("data-versao-antes", str(unidade["versao"]))
    expect(aviso).to_have_attribute("data-versao-depois", str(depois["versao"]))
    expect(aviso).to_have_attribute("data-atualizado-depois", depois["atualizado_em"])
    expect(pagina.locator("[data-ref=versao]")).to_have_text(str(depois["versao"]))
    expect(pagina.locator("[data-ref=ficha]")).to_have_attribute(
        "data-etag", f'"{depois["versao"]}"'
    )
    expect(pagina.locator("[data-ref=atualizado-em]")).to_have_attribute(
        "data-iso", depois["atualizado_em"]
    )
    gravada = api(pagina, token_, f"/unidades/{unidade['id']}")
    assert (gravada["telefone"], gravada["bairro"], gravada["versao"]) == (
        "8131310000",
        "Casa Amarela",
        depois["versao"],
    )
    eventos = api(pagina, token_, f"/unidades/{unidade['id']}/historico")["itens"]
    assert eventos[0]["acao"] == "unidade.atualizada"


def test_dois_navegadores_a_segunda_gravacao_recebe_412_e_nada_e_sobrescrito(
    sessao_de: Sessao, navegador: Browser, senha_demo: str, autenticador: Autenticador
) -> None:
    primeira = sessao_de("GESTOR_DADOS")
    token_ = token(primeira)
    unidade = nova_unidade(primeira, token_)
    # Outro navegador: contexto próprio (cookies e sessão separados), com login próprio.
    contexto = novo_contexto(navegador)
    try:
        segunda = contexto.new_page()
        entrar(segunda, USUARIOS["GESTOR_DADOS"], senha_demo, autenticador)
        _abrir(primeira, unidade["id"])
        _abrir(segunda, unidade["id"])

        _editar(primeira, {"telefone": "8130000001"})  # a primeira abre a edição e para no diff
        _editar(segunda, {"telefone": "8130000002"})
        with segunda.expect_response(lambda r: r.request.method == "PATCH") as gravou:
            segunda.click("#fe-enviar")
        assert gravou.value.status == 200

        with primeira.expect_response(lambda r: r.request.method == "PATCH") as recusou:
            primeira.click("#fe-enviar")
        assert recusou.value.status == 412
        assert recusou.value.request.headers["if-match"] == f'"{unidade["versao"]}"'
        aviso = primeira.locator("[data-ref=aviso-edicao]")
        expect(aviso).to_have_attribute("data-tipo", "conflito")
        expect(aviso).to_have_attribute("data-versao-lida", str(unidade["versao"]))
        expect(aviso).to_have_attribute("data-versao-atual", str(unidade["versao"] + 1))
        expect(aviso).to_contain_text("nada foi sobrescrito")
        expect(primeira.locator("[data-ref=versao]")).to_have_text(str(unidade["versao"] + 1))
        gravada = api(primeira, token_, f"/unidades/{unidade['id']}")
        assert gravada["telefone"] == "8130000002"  # a gravação do outro navegador ficou
    finally:
        contexto.close()


def test_edicao_nao_reativa_unidade_inativa(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)
    api(pagina, token_, f"/unidades/{unidade['id']}/desativar", "POST", {"motivo": "Teste da T9"})
    _abrir(pagina, unidade["id"])
    pagina.click("[data-ref=editar]")
    expect(pagina.locator("[data-ref=status-inativa]")).to_be_disabled()
    pagina.fill("#fld-nome", f"{unidade['nome']} (renomeada)")
    pagina.click("#fe-enviar")
    with pagina.expect_response(lambda r: r.request.method == "PATCH") as resposta:
        pagina.click("#fe-enviar")
    assert resposta.value.request.post_data_json == {"nome": f"{unidade['nome']} (renomeada)"}
    gravada = api(pagina, token_, f"/unidades/{unidade['id']}")
    assert gravada["status"] == "inativa"
    expect(pagina.locator("[data-ref=status]")).to_have_text("Inativa")


def test_edicao_de_unidade_ativa_nao_oferece_desativar_pelo_formulario(
    gestor: tuple[Page, str],
) -> None:
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)
    _abrir(pagina, unidade["id"])
    pagina.click("[data-ref=editar]")
    opcoes = pagina.locator("#fld-status option").evaluate_all("os => os.map(o => o.value)")
    assert "inativa" not in opcoes  # desativar só pela procedure (T25)


@pytest.mark.parametrize("papel", ["TECNICO_DISTRITAL", "GESTOR_UNIDADE", "COORD_TECNICO"])
def test_quem_so_propoe_nao_edita_nem_cadastra(sessao_de: Sessao, papel: str) -> None:
    pagina = sessao_de(papel)
    token_ = token(pagina)
    me = api(pagina, token_, "/me")
    escopo = me["permissoes"]["unidade:update"][0]
    if escopo["tipo"] == "unidade":
        unidade_id = escopo["id"]
    elif escopo["tipo"] == "distrito":
        unidade_id = api(pagina, token_, f"/unidades?distrito={escopo['id']}&tamanho=1")["itens"][
            0
        ]["id"]
    else:
        unidade_id = api(pagina, token_, f"/dashboard/inventario?area={escopo['id']}&tamanho=1")[
            "itens"
        ][0]["unit_id"]
    _abrir(pagina, str(unidade_id))
    expect(pagina.locator("[data-ref=editar]")).to_have_count(0)
    propor = pagina.locator("[data-ref=propor]")
    expect(propor).to_be_disabled()
    expect(propor).to_contain_text("em desenvolvimento")
    pagina.goto("/#/nova")
    expect(pagina.locator("[data-estado=em-desenvolvimento]")).to_be_visible()
    expect(pagina.locator("#fn")).to_have_count(0)


def test_diretoria_nao_ve_edicao_nem_cadastro_e_a_api_nega(sessao_de: Sessao) -> None:
    pagina = sessao_de("DIRETORIA")
    token_ = token(pagina)
    unidade = api(pagina, token_, "/unidades?tamanho=1")["itens"][0]
    lida = _abrir(pagina, unidade["id"])
    expect(pagina.locator("[data-ref=editar], [data-ref=propor]")).to_have_count(0)
    pagina.goto("/#/nova")
    expect(pagina.locator("[data-estado=sem-acesso]")).to_be_visible()
    negado = requisicao(
        pagina,
        token_,
        "PATCH",
        f"/unidades/{unidade['id']}",
        {"telefone": "8100000000"},
        {"If-Match": lida.headers["etag"]},
    )
    assert negado.status == 403


@pytest.mark.parametrize("largura", [1280, 390])
def test_sem_rolagem_horizontal(gestor: tuple[Page, str], largura: int) -> None:
    pagina, token_ = gestor
    pagina.set_viewport_size({"width": largura, "height": 900})
    _abrir_cadastro(pagina)
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    unidade = nova_unidade(pagina, token_)
    _abrir(pagina, unidade["id"])
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    _editar(pagina, {"telefone": "8139990000"})
    expect(pagina.locator("[data-ref=diff]")).to_be_visible()
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
