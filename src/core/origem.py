"""De onde veio a requisição, para a auditoria e para a sessão de login (spec 013, T3).

Um lugar só para IP, User-Agent e request id (013/R3.2, R3.4, R3.5):
- IP: o endereço da conexão (`request.client`), depois do `ProxyHeadersMiddleware` do uvicorn,
  que só aceita `X-Forwarded-For` de um proxy da lista de confiáveis (`FORWARDED_ALLOW_IPS`; a
  lista é configurada na 013/T4). A aplicação nunca lê `X-Forwarded-For`, `X-Real-IP` nem
  `Forwarded` por conta própria. Um host que não seja IP (cliente de teste) fica sem IP.
- User-Agent: declaração do cliente, sem caracteres de controle e com até 200 caracteres. Nenhum
  outro cabeçalho é coletado (sem impressão digital do dispositivo).
"""

import ipaddress
import unicodedata
from dataclasses import dataclass

from starlette.requests import Request

USER_AGENT_MAX = 200
"""O mesmo limite da coluna `audit_log.user_agent` (migração 0013_01)."""


@dataclass(frozen=True, slots=True)
class OrigemDaRequisicao:
    ip: str | None
    user_agent: str | None
    request_id: str | None


def origem_da_requisicao(request: Request) -> OrigemDaRequisicao:
    host = request.client.host if request.client else None
    return OrigemDaRequisicao(
        ip=_ip(host),
        user_agent=limpar_user_agent(request.headers.get("user-agent")),
        request_id=getattr(request.state, "request_id", None),
    )


def limpar_user_agent(valor: str | None) -> str | None:
    """Sem caracteres de controle (categoria Unicode `Cc`, que inclui CR, LF, TAB, NUL e DEL),
    sem espaços nas pontas e cortado em 200; vazio vira ausente."""
    if valor is None:
        return None
    limpo = "".join(c for c in valor if unicodedata.category(c) != "Cc").strip()
    return limpo[:USER_AGENT_MAX].rstrip() or None


def _ip(host: str | None) -> str | None:
    if not host:
        return None
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        return None
