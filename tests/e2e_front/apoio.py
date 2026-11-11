"""Acesso à API nos E2E do front: o teste compara a tela com a resposta da API no mesmo instante.

O access token fica só na memória do front (R2.3); o teste o obtém pelo refresh da própria
sessão do papel e chama a API pelo contexto do navegador (mesmo domínio, mesma CA de teste).
"""

import secrets
from typing import Any

from playwright.sync_api import APIResponse, Page, expect


def token(pagina: Page) -> str:
    with pagina.expect_response("**/api/v1/auth/refresh") as resposta:
        pagina.reload()
    expect(pagina.locator(".shell")).to_be_visible()
    valor: str = resposta.value.json()["access_token"]
    return valor


def requisicao(
    pagina: Page,
    token_: str,
    metodo: str,
    caminho: str,
    corpo: dict[str, Any] | None = None,
    cabecalhos: dict[str, str] | None = None,
) -> APIResponse:
    return pagina.request.fetch(
        f"/api/v1{caminho}",
        method=metodo,
        data=corpo,
        headers={"Authorization": f"Bearer {token_}", **(cabecalhos or {})},
    )


def api(
    pagina: Page,
    token_: str,
    caminho: str,
    metodo: str = "GET",
    corpo: dict[str, Any] | None = None,
) -> Any:
    resposta = requisicao(pagina, token_, metodo, caminho, corpo)
    assert resposta.ok, resposta.text()
    return resposta.json()


def nova_unidade(pagina: Page, token_: str) -> dict[str, Any]:
    """Unidade criada pela API no banco descartável do E2E, para o teste não mexer no seed."""
    tipo = next(t for t in api(pagina, token_, "/referencias/tipos-unidade") if t["ativo"])
    distrito = api(pagina, token_, "/referencias/distritos")[0]
    corpo = {
        "nome": f"Unidade de teste da ficha {secrets.token_hex(3)}",
        "tipo_unidade_id": tipo["id"],
        "distrito_id": distrito["id"],
        "cep": "50000-000",
        "endereco": "Rua de Teste, 1",
        "status": "ativa",
    }
    criada: dict[str, Any] = api(pagina, token_, "/unidades", "POST", corpo)
    return criada
