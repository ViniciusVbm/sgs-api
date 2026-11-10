"""Estados de carregando e de erro (spec 012, T3: R1.6). O estado vazio é provado na lista (T7)."""

import json
from collections.abc import Callable

from playwright.sync_api import Page, Route, expect


def test_carregando_enquanto_a_api_nao_responde(sessao_de: Callable[[str], Page]) -> None:
    pagina = sessao_de("DIRETORIA")
    retidas: list[Route] = []
    pagina.route("**/api/v1/me", lambda rota: retidas.append(rota))  # segura a resposta
    pagina.reload()
    carregando = pagina.locator("[data-estado=carregando]")
    expect(carregando).to_be_visible()
    expect(carregando).to_have_attribute("aria-busy", "true")
    retidas[0].continue_()  # libera a resposta retida; só então a interface segue
    expect(pagina.locator(".shell")).to_be_visible()


def test_erro_mostra_o_detail_da_api_e_o_codigo_do_pedido(sessao_de: Callable[[str], Page]) -> None:
    pagina = sessao_de("DIRETORIA")
    problema = {
        "title": "Internal Server Error",
        "status": 500,
        "detail": "Falha provocada pelo teste.",
    }
    pagina.route(
        "**/api/v1/me",
        lambda rota: rota.fulfill(
            status=500,
            content_type="application/problem+json",
            headers={"X-Request-ID": "req-teste-123"},
            body=json.dumps(problema),
        ),
    )
    pagina.reload()
    erro = pagina.locator("[data-estado=erro]")
    expect(erro).to_be_visible()
    expect(erro).to_have_attribute("role", "alert")
    expect(erro).to_contain_text("Falha provocada pelo teste.")
    expect(erro).to_contain_text("req-teste-123")
