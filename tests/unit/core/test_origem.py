"""Origem da requisição para a auditoria: IP e User-Agent (spec 013, T3; R3.2, R3.4, R3.5)."""

from typing import Any, cast

import httpx
from starlette.requests import Request
from starlette.types import Receive, Scope, Send
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from src.core.origem import USER_AGENT_MAX, limpar_user_agent, origem_da_requisicao

PROXY = "10.231.1.2"


async def _eco(scope: Scope, receive: Receive, send: Send) -> None:
    """App ASGI mínima que responde o que `origem_da_requisicao` viu."""
    origem = origem_da_requisicao(Request(scope, receive))
    corpo = f"{origem.ip}|{origem.user_agent}".encode()
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": corpo})


async def _origem_vista(
    cliente: tuple[str, int], cabecalhos: dict[str, str], *, confiaveis: str = PROXY
) -> list[str]:
    # Os tipos ASGI do uvicorn e os do Starlette/httpx não se casam no mypy; em execução são iguais.
    app: Any = ProxyHeadersMiddleware(cast(Any, _eco), trusted_hosts=confiaveis)
    transporte = httpx.ASGITransport(app=app, client=cliente)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as http:
        resposta = await http.get("/", headers=cabecalhos)
    return resposta.text.split("|")


def test_user_agent_cortado_e_sem_controle() -> None:
    """013/R3.4: até 200 caracteres, sem caracteres de controle; vazio vira ausente."""
    assert limpar_user_agent("Mozilla/5.0\r\nX-Injetado: 1\x00\x7f") == "Mozilla/5.0X-Injetado: 1"
    assert limpar_user_agent("a" * 500) == "a" * USER_AGENT_MAX
    assert limpar_user_agent("  curl/8.0  ") == "curl/8.0"
    assert limpar_user_agent("\x01\x02") is None
    assert limpar_user_agent("") is None
    assert limpar_user_agent(None) is None


async def test_cliente_nao_confiavel_nao_escolhe_ip() -> None:
    """013/R3.2: fora da lista de proxies confiáveis, vale o endereço da conexão."""
    ip, _ = await _origem_vista(("203.0.113.9", 5000), {"X-Forwarded-For": "6.6.6.6"})

    assert ip == "203.0.113.9"


async def test_x_real_ip_e_forwarded_nao_tem_efeito() -> None:
    """013/R3.2: `X-Real-IP` e `Forwarded` nunca são fonte de IP, nem vindos do proxy."""
    falsos = {"X-Real-IP": "6.6.6.6", "Forwarded": "for=6.6.6.6"}

    de_fora, _ = await _origem_vista(("203.0.113.9", 5000), falsos)
    do_proxy, _ = await _origem_vista((PROXY, 5000), falsos)

    assert de_fora == "203.0.113.9"
    assert do_proxy == PROXY


async def test_proxy_confiavel_repassa_ip_real() -> None:
    """013/R3.2: do proxy confiável, o IP é o que ele pôs no `X-Forwarded-For`; o User-Agent vem
    do cabeçalho, já limpo."""
    ip, user_agent = await _origem_vista(
        (PROXY, 5000), {"X-Forwarded-For": "198.51.100.7", "User-Agent": "Firefox\t/130"}
    )

    assert ip == "198.51.100.7"
    assert user_agent == "Firefox/130"


async def test_sem_cliente_ou_host_invalido_fica_sem_ip() -> None:
    """013/R3.2: sem endereço de conexão, ou com um que não é IP, o evento fica sem IP."""
    sem_cliente = Request({"type": "http", "headers": [], "client": None})
    com_nome = Request({"type": "http", "headers": [], "client": ("testclient", 50000)})

    assert origem_da_requisicao(sem_cliente).ip is None
    assert origem_da_requisicao(com_nome).ip is None
    assert origem_da_requisicao(sem_cliente).user_agent is None
