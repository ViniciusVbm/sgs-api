"""Lista de unidades (spec 012, T7: R5.1, R5.2; vazio do R1.6, que fecha a T3; recorte do R3.5)."""

import re
import unicodedata
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, expect


def _abrir(pagina: Page, hash_: str) -> dict[str, Any]:
    pagina.goto("/#/sem-acesso")
    with pagina.expect_response(re.compile(r".*/api/v1/unidades\?.*")) as resposta:
        pagina.goto(f"/{hash_}")
    assert resposta.value.status == 200
    dados: dict[str, Any] = resposta.value.json()
    dados["_consulta"] = parse_qs(urlparse(resposta.value.url).query)
    return dados


def test_lista_mostra_a_pagina_da_api_com_nomes_das_referencias(
    sessao_de: Callable[[str], Page],
) -> None:
    pagina = sessao_de("GESTOR_DADOS")
    lista = _abrir(pagina, "#/unidades")
    linhas = pagina.locator("#resultado tbody tr")
    expect(linhas).to_have_count(len(lista["itens"]))
    assert lista["_consulta"]["pagina"] == ["1"]
    assert lista["_consulta"]["tamanho"] == ["20"]
    expect(pagina.locator("#count")).to_have_text(
        f"1\u2013{len(lista['itens'])} de {lista['total']} unidades"
    )
    primeira = lista["itens"][0]
    expect(linhas.first.locator(".t-name")).to_have_text(primeira["nome"])
    # Tipo e distrito vêm de /referencias (a lista só tem ids).
    for coluna in (2, 3):
        textos = linhas.locator(f"td:nth-child({coluna})").all_inner_texts()
        assert textos
        assert all(t.strip() not in ("", "—") for t in textos)
    expect(pagina.locator("[data-estado=em-desenvolvimento]")).to_be_disabled()  # exportar (R5.4)


def test_filtros_vao_para_a_api_e_ficam_na_url(sessao_de: Callable[[str], Page]) -> None:
    pagina = sessao_de("GESTOR_DADOS")
    _abrir(pagina, "#/unidades")
    distrito = pagina.locator("#fds option").nth(1).get_attribute("value")
    assert distrito
    with pagina.expect_request(re.compile(r".*/api/v1/unidades\?.*")) as pedido:
        pagina.select_option("#fds", distrito)
    assert parse_qs(urlparse(pedido.value.url).query)["distrito"] == [distrito]
    expect(pagina).to_have_url(re.compile(rf"#/unidades\?distrito={distrito}$"))
    with pagina.expect_request(re.compile(r".*/api/v1/unidades\?.*")) as pedido:
        pagina.select_option("#ford", "atualizacao")
    consulta = parse_qs(urlparse(pedido.value.url).query)
    assert consulta["ordem"] == ["atualizacao"]
    assert consulta["distrito"] == [distrito]
    # Recarregar mantém a mesma lista (filtros na URL).
    with pagina.expect_request(re.compile(r".*/api/v1/unidades\?.*")) as pedido:
        pagina.reload()
    assert parse_qs(urlparse(pedido.value.url).query)["ordem"] == ["atualizacao"]


def test_busca_e_busca_do_topo(sessao_de: Callable[[str], Page]) -> None:
    pagina = sessao_de("GESTOR_DADOS")
    _abrir(pagina, "#/unidades")
    with pagina.expect_response(re.compile(r".*/api/v1/unidades\?.*q=CAPS.*")) as resposta:
        pagina.fill("#q", "CAPS")
    nomes = pagina.locator("#resultado .t-name").all_inner_texts()
    assert len(nomes) == len(resposta.value.json()["itens"]) > 0
    assert all("caps" in n.lower() for n in nomes)
    pagina.goto("/#/inicio")
    pagina.fill("#topQ", "CAPS")
    pagina.press("#topQ", "Enter")
    expect(pagina).to_have_url(re.compile(r"#/unidades\?q=CAPS$"))


def test_busca_sem_acento_caixa_nem_espacos_pela_fn_normalize_name(
    sessao_de: Callable[[str], Page],
) -> None:
    """T26: a busca usa `name_normalized`, coluna gerada por `fn_normalize_name` (unaccent, caixa
    e espaços), e o índice trigram dela: "SAUDE   casa" acha "Centro de Saúde Casa Amarela"."""
    pagina = sessao_de("GESTOR_DADOS")
    todas = _abrir(pagina, "#/unidades?tamanho=100")["itens"]
    alvo = next(
        u
        for u in todas
        if u["nome"] != unicodedata.normalize("NFKD", u["nome"]).encode("ascii", "ignore").decode()
    )
    sem_acento = unicodedata.normalize("NFKD", alvo["nome"]).encode("ascii", "ignore").decode()
    palavras = sem_acento.split()
    busca = "   ".join(p.upper() if i % 2 == 0 else p.lower() for i, p in enumerate(palavras[-2:]))
    assert busca not in alvo["nome"]  # nem acento, nem caixa, nem espaços iguais aos do nome
    with pagina.expect_response(re.compile(r".*/api/v1/unidades\?.*q=.*")) as resposta:
        pagina.fill("#q", busca)
    assert any(u["id"] == alvo["id"] for u in resposta.value.json()["itens"])
    expect(pagina.locator(f"#resultado tr[data-id='{alvo['id']}']")).to_be_visible()


def test_sem_resultado_mostra_o_estado_vazio(sessao_de: Callable[[str], Page]) -> None:
    """R1.6 (fecha a T3)."""
    pagina = sessao_de("GESTOR_DADOS")
    lista = _abrir(pagina, "#/unidades?q=nao-existe-unidade-assim")
    assert lista["total"] == 0
    expect(pagina.locator("#resultado [data-estado=vazio]")).to_contain_text(
        "Nenhuma unidade encontrada"
    )
    expect(pagina.locator("#count")).to_have_text("0 unidades")


def test_paginacao_e_pagina_alem_da_ultima(sessao_de: Callable[[str], Page]) -> None:
    """R5.2"""
    pagina = sessao_de("GESTOR_DADOS")
    lista = _abrir(pagina, "#/unidades")
    assert lista["total"] > 20  # o seed de demonstração tem mais de uma página
    with pagina.expect_response(re.compile(r".*/api/v1/unidades\?.*pagina=2.*")) as resposta:
        pagina.click("#resultado [data-pagina='2']")
    expect(pagina.locator("#resultado tbody tr")).to_have_count(len(resposta.value.json()["itens"]))
    expect(pagina).to_have_url(re.compile(r"pagina=2"))
    alem = _abrir(pagina, "#/unidades?pagina=99")
    assert alem["itens"] == []
    expect(pagina.locator("#resultado [data-estado=vazio]")).to_contain_text("além da última")


def test_tecnico_distrital_abre_no_proprio_distrito_e_pode_ver_todos(
    sessao_de: Callable[[str], Page],
) -> None:
    """R3.5: recorte de navegação, não restrição; a leitura é global pela matriz atual."""
    pagina = sessao_de("TECNICO_DISTRITAL")
    pagina.goto("/#/sem-acesso")
    with pagina.expect_response(re.compile(r".*/api/v1/unidades\?.*")) as resposta:
        pagina.goto("/#/unidades")
    do_distrito = resposta.value.json()
    distrito = parse_qs(urlparse(resposta.value.url).query)["distrito"]
    expect(pagina).to_have_url(re.compile(rf"#/unidades\?distrito={distrito[0]}$"))
    expect(pagina.locator("h1")).to_have_text(re.compile(r"^Unidades do "))
    with pagina.expect_response(re.compile(r".*/api/v1/unidades\?.*")) as todas:
        pagina.select_option("#fds", "")
    assert "distrito" not in parse_qs(urlparse(todas.value.url).query)
    assert todas.value.json()["total"] > do_distrito["total"]
    expect(pagina).to_have_url(re.compile(r"distrito=todos"))
