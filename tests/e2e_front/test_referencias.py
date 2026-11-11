"""Tabelas de referência: incluir, consultar, alterar, desativar e reativar os tipos de unidade,
de equipamento e de serviço, e o ON UPDATE CASCADE do código do tipo de equipamento
(spec 012, T24: R16.1; R3.2, R3.3).

Cada teste cria os próprios itens, com código único. O único dado do seed alterado é o código
de um tipo de equipamento, que o teste da cascata restaura (design § Dados nos E2E da emenda).
"""

import secrets
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.e2e_front.apoio import api, requisicao, token

Sessao = Callable[[str], Page]
EDITAVEIS = ["tipos-unidade", "tipos-equipamento", "tipos-servico"]


def _codigo(prefixo: str) -> str:
    return f"E2E_{prefixo}_{secrets.token_hex(3).upper()}"


def _abrir(pagina: Page, tabela: str) -> None:
    with pagina.expect_response(f"**/api/v1/referencias/{tabela}"):
        pagina.goto("/#/sem-acesso")
        pagina.goto(f"/#/referencias?tabela={tabela}")
    expect(pagina.locator("[data-ref=contagem]")).to_be_visible()


def _item(pagina: Page, token_: str, tabela: str, codigo: str) -> dict[str, Any]:
    itens = api(pagina, token_, f"/referencias/{tabela}")
    return next(i for i in itens if i["codigo"] == codigo)


def _equipamentos_por_codigo(pagina: Page, token_: str) -> dict[str, int]:
    """Todos os equipamentos por código de tipo: em unidades (consulta do painel) e sem unidade."""
    contagem: dict[str, int] = {}
    for linha in api(pagina, token_, "/dashboard/consultas/equipamentos-por-tipo-e-distrito"):
        codigo = linha["equipment_type_code"]
        contagem[codigo] = contagem.get(codigo, 0) + linha["equipment_count"]
    for equipamento in api(pagina, token_, "/equipamentos"):
        contagem[equipamento["tipo_codigo"]] = contagem.get(equipamento["tipo_codigo"], 0) + 1
    return contagem


@pytest.fixture
def gestor(sessao_de: Sessao) -> Iterator[tuple[Page, str]]:
    pagina = sessao_de("GESTOR_DADOS")
    yield pagina, token(pagina)
    pagina.close()


@pytest.mark.parametrize("tabela", EDITAVEIS)
def test_incluir_alterar_desativar_e_reativar(gestor: tuple[Page, str], tabela: str) -> None:
    pagina, token_ = gestor
    exclusoes: list[str] = []
    pagina.on("request", lambda r: exclusoes.append(r.url) if r.method == "DELETE" else None)
    codigo = _codigo(tabela.split("-")[1][:4].upper())
    _abrir(pagina, tabela)
    expect(pagina.locator("[data-ref=regra-exclusao]")).to_contain_text("Excluir é desativar")
    expect(pagina.get_by_role("button", name="Excluir")).to_have_count(0)

    # Incluir
    pagina.click("#incluir")
    pagina.fill("#fld-codigo", codigo)
    pagina.fill("#fld-nome", f"Item de teste {codigo}")
    if tabela == "tipos-unidade":
        area = api(pagina, token_, "/referencias/areas-tecnicas")[0]
        pagina.select_option("#fld-area_tecnica_id", str(area["id"]))
    with pagina.expect_response(f"**/api/v1/referencias/{tabela}") as criacao:
        pagina.click("#fr button[type=submit]")
    assert criacao.value.status == 201
    linha = pagina.locator(f"tr[data-codigo='{codigo}']")
    expect(linha.locator("[data-ref=situacao]")).to_have_text("Ativo")
    item = _item(pagina, token_, tabela, codigo)
    assert item["ativo"] is True
    if tabela == "tipos-unidade":
        assert item["area_tecnica_id"] == area["id"]

    # Consultar e alterar: o PATCH leva só o campo alterado
    linha.locator("[data-editar]").click()
    expect(pagina.locator("#fld-codigo")).to_have_value(codigo)
    novo_nome = f"Item renomeado {codigo}"
    pagina.fill("#fld-nome", novo_nome)
    with pagina.expect_request(lambda r: r.method == "PATCH") as alteracao:
        pagina.click("#fr button[type=submit]")
    assert alteracao.value.post_data_json == {"nome": novo_nome}
    expect(linha).to_contain_text(novo_nome)
    assert _item(pagina, token_, tabela, codigo)["nome"] == novo_nome

    # Desativar (exclusão lógica) e reativar
    for ativo, rotulo in ((False, "Inativo"), (True, "Ativo")):
        linha.locator("[data-ativo]").click()
        with pagina.expect_request(lambda r: r.method == "PATCH") as pedido:
            pagina.click("#sit-confirmar")
        assert pedido.value.post_data_json == {"ativo": ativo}
        expect(linha.locator("[data-ref=situacao]")).to_have_text(rotulo)
        assert _item(pagina, token_, tabela, codigo)["ativo"] is ativo
    assert exclusoes == []  # nenhuma exclusão física


def test_tipo_de_unidade_sem_area_mostra_o_erro_da_api_no_campo(gestor: tuple[Page, str]) -> None:
    pagina, _ = gestor
    _abrir(pagina, "tipos-unidade")
    pagina.click("#incluir")
    pagina.fill("#fld-codigo", _codigo("SEMAREA"))
    pagina.fill("#fld-nome", "Tipo sem área")
    with pagina.expect_response("**/api/v1/referencias/tipos-unidade") as resposta:
        pagina.click("#fr button[type=submit]")
    assert resposta.value.status == 422
    erro = resposta.value.json()["errors"][0]
    assert erro["campo"] == "area_tecnica_id"
    caixa = pagina.locator("[data-campo=area_tecnica_id]")
    expect(caixa).to_have_class("fld bad")
    expect(caixa.locator(".fld-err")).to_have_text(erro["mensagem"])


def test_codigo_repetido_mostra_o_409_no_campo_codigo(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    existente = api(pagina, token_, "/referencias/tipos-servico")[0]
    _abrir(pagina, "tipos-servico")
    pagina.click("#incluir")
    pagina.fill("#fld-codigo", existente["codigo"])
    pagina.fill("#fld-nome", "Duplicado")
    with pagina.expect_response("**/api/v1/referencias/tipos-servico") as resposta:
        pagina.click("#fr button[type=submit]")
    assert resposta.value.status == 409
    caixa = pagina.locator("[data-campo=codigo]")
    expect(caixa).to_have_class("fld bad")
    expect(caixa.locator(".fld-err")).to_have_text(resposta.value.json()["detail"])


def _trocar_codigo(pagina: Page, item_id: int, de: str, para: str) -> None:
    linha = pagina.locator(f"tr[data-item='{item_id}']")
    expect(linha).to_have_attribute("data-codigo", de)
    linha.locator("[data-editar]").click()
    pagina.fill("#fld-codigo", para)
    with pagina.expect_request(lambda r: r.method == "PATCH") as pedido:
        pagina.click("#fr button[type=submit]")
    assert pedido.value.post_data_json == {"codigo": para}
    expect(pagina.locator("[data-ref=resultado-cascata]")).to_be_visible()


def _conferir_cascata(pagina: Page, token_: str, item_id: int, esperado: int) -> None:
    eventos = api(
        pagina,
        token_,
        f"/auditoria/eventos?entidade_tipo=referencia&entidade_id=tipos-equipamento:{item_id}"
        "&acao=referencia.atualizada&tamanho=1",
    )
    afetados = eventos["itens"][0]["metadados"]["equipamentos_afetados"]
    assert afetados == esperado
    painel = pagina.locator("[data-ref=resultado-cascata]")
    expect(painel).to_have_attribute("data-afetados", str(afetados))
    expect(painel).to_have_attribute("data-confere", "true")
    expect(painel).to_have_attribute("data-antigos", "0")
    expect(painel).to_contain_text(f"{afetados} equipamentos afetados")


def test_trocar_o_codigo_do_tipo_de_equipamento_cascateia_nos_equipamentos(
    gestor: tuple[Page, str],
) -> None:
    pagina, token_ = gestor
    antes = _equipamentos_por_codigo(pagina, token_)
    original = max(
        antes, key=lambda c: antes[c]
    )  # o tipo com mais equipamentos (em unidades e soltos)
    quantidade = antes[original]
    assert quantidade > 0
    item = _item(pagina, token_, "tipos-equipamento", original)
    novo = f"{original[:30]}_E2E"
    _abrir(pagina, "tipos-equipamento")
    try:
        _trocar_codigo(pagina, item["id"], original, novo)
        _conferir_cascata(pagina, token_, item["id"], quantidade)
        depois = _equipamentos_por_codigo(pagina, token_)
        assert depois.get(novo) == quantidade  # os registros relacionados têm o código novo
        assert original not in depois
        # Restaura pela própria tela (de novo pela cascata)
        _trocar_codigo(pagina, item["id"], novo, original)
        _conferir_cascata(pagina, token_, item["id"], quantidade)
    finally:  # restaura o código do seed mesmo se uma asserção falhar no meio
        tipos = api(pagina, token_, "/referencias/tipos-equipamento")
        atual = next(i for i in tipos if i["id"] == item["id"])
        if atual["codigo"] != original:
            caminho = f"/referencias/tipos-equipamento/{item['id']}"
            api(pagina, token_, caminho, "PATCH", {"codigo": original})
    assert _equipamentos_por_codigo(pagina, token_) == antes


@pytest.mark.parametrize("tabela", ["distritos", "areas-tecnicas"])
def test_dominios_fechados_sao_somente_leitura(gestor: tuple[Page, str], tabela: str) -> None:
    pagina, token_ = gestor
    _abrir(pagina, tabela)
    expect(pagina.locator("[data-ref=somente-leitura]")).to_be_visible()
    expect(pagina.locator("#incluir")).to_have_count(0)
    expect(pagina.locator("[data-editar], [data-ativo]")).to_have_count(0)
    expect(pagina.locator("tr[data-item]")).to_have_count(
        len(api(pagina, token_, f"/referencias/{tabela}"))
    )


@pytest.mark.parametrize("papel", ["TECNICO_DISTRITAL", "COORD_TECNICO", "DIRETORIA", "AUDITOR"])
def test_outros_papeis_nao_gerenciam_referencias(sessao_de: Sessao, papel: str) -> None:
    pagina = sessao_de(papel)
    expect(pagina.locator(".nav a", has_text="Tabelas de referência")).to_have_count(0)
    pagina.goto("/#/referencias?tabela=tipos-servico")
    expect(pagina.locator("[data-estado=sem-acesso]")).to_be_visible()
    resposta = requisicao(
        pagina,
        token(pagina),
        "POST",
        "/referencias/tipos-servico",
        {"codigo": _codigo("NEGADO"), "nome": "x"},
    )
    assert resposta.status == 403  # a API nega, não só a tela


@pytest.mark.parametrize("largura", [1280, 390])
def test_sem_rolagem_horizontal(gestor: tuple[Page, str], largura: int) -> None:
    pagina, _ = gestor
    pagina.set_viewport_size({"width": largura, "height": 900})
    for tabela in EDITAVEIS:
        _abrir(pagina, tabela)
        assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), tabela
    pagina.click("#incluir")
    expect(pagina.locator("#fr")).to_be_visible()
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
