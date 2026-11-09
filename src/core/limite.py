"""Limite de requisições por IP (spec 002, R1.5; ADR-0007, emenda de 09/11/2026).

Janela móvel em memória, por processo, com a biblioteca `limits` (o motor do slowapi). Um
limitador por app, montado pela raiz de composição: cada app (e cada teste) começa zerado. Atrás
do proxy, o IP é o do cliente, que o uvicorn lê dos cabeçalhos `X-Forwarded-*`.
"""

from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter

from src.core.errors import TooManyRequests


class LimiteDeRequisicoes:
    def __init__(self, limite: str) -> None:
        self._item = parse(limite)
        self._limitador = MovingWindowRateLimiter(MemoryStorage())

    def conferir(self, chave: str) -> None:
        """Conta a requisição de `chave`; levanta 429 se passou do limite."""
        if not self._limitador.hit(self._item, chave):
            raise TooManyRequests(
                "Muitas tentativas de login. Aguarde um minuto.",
                extensoes={"retry_after": "60"},
            )
