"""Início com GET /dashboard/resumo no escopo do papel (spec 012, T6: R4.1)."""

from collections.abc import Callable
from typing import Any

import pytest
from playwright.sync_api import Page, expect


def _abrir_inicio(pagina: Page) -> dict[str, Any]:
    with pagina.expect_response("**/api/v1/dashboard/resumo") as resposta:
        pagina.goto("/#/sem-acesso")
        pagina.goto("/#/inicio")
    assert resposta.value.status == 200
    dados: dict[str, Any] = resposta.value.json()
    return dados


def _numero(pagina: Page, ref: str) -> int:
    return int(pagina.locator(f"[data-ref={ref}] .v").inner_text())


@pytest.mark.parametrize("papel", ["GESTOR_DADOS", "TECNICO_DISTRITAL"])
def test_numeros_da_tela_sao_os_da_api(sessao_de: Callable[[str], Page], papel: str) -> None:
    pagina = sessao_de(papel)
    resumo = _abrir_inicio(pagina)
    expect(pagina.locator("[data-ref=indicadores]")).to_be_visible()
    assert _numero(pagina, "total") == resumo["unidades"]["total"]
    assert _numero(pagina, "pendencias") == resumo["qualidade"]["unidades_com_pendencias"]
    assert _numero(pagina, "sem-cnes") == resumo["qualidade"]["sem_cnes"]
    assert _numero(pagina, "alteracoes") == resumo["alteracoes"]["ultimos_7_dias"]
    distritos = len(resumo["unidades"]["por_distrito"])
    tipos = len(resumo["unidades"]["por_tipo"])
    areas = len(resumo["unidades"]["por_area"])
    status = len(resumo["unidades"]["por_status"])
    expect(pagina.locator("[data-ref=barra]")).to_have_count(distritos + tipos + areas + status)


def test_o_escopo_do_distrito_reduz_os_numeros(sessao_de: Callable[[str], Page]) -> None:
    """R4.1: dashboard:read do Técnico Distrital é de distrito (011/T22); só o DS dele aparece."""
    central = _abrir_inicio(sessao_de("GESTOR_DADOS"))
    distrito = _abrir_inicio(sessao_de("TECNICO_DISTRITAL"))
    assert distrito["unidades"]["total"] < central["unidades"]["total"]
    assert len(distrito["unidades"]["por_distrito"]) == 1


def test_barra_leva_a_lista_filtrada(sessao_de: Callable[[str], Page]) -> None:
    pagina = sessao_de("GESTOR_DADOS")
    resumo = _abrir_inicio(pagina)
    primeiro = resumo["unidades"]["por_distrito"][0]
    with pagina.expect_request("**/api/v1/unidades?*") as pedido:
        pagina.locator("[data-ref=barra]").first.click()
    assert f"distrito={primeiro['chave']}" in pedido.value.url
