"""UUID v7 (RFC 9562) só com a biblioteca padrão, porque o Python 3.13 não tem `uuid.uuid7`.

Os 48 bits iniciais são os milissegundos Unix, então os IDs ordenam pela hora de criação; os
74 bits restantes (fora versão e variante) são sorteados com `secrets`.
"""

import secrets
import time
from uuid import UUID

_MAX_UNIX_MS = (1 << 48) - 1
_VERSION = 0x7
_VARIANT = 0b10  # RFC 4122/9562


def uuid7(*, unix_ms: int | None = None) -> UUID:
    """Novo UUID v7. `unix_ms` fixa o instante (por padrão, o relógio do sistema)."""
    instante = time.time_ns() // 1_000_000 if unix_ms is None else unix_ms
    if not 0 <= instante <= _MAX_UNIX_MS:
        raise ValueError("o instante do UUID v7 precisa caber em 48 bits de milissegundos")
    valor = (
        instante << 80
        | _VERSION << 76
        | secrets.randbits(12) << 64
        | _VARIANT << 62
        | secrets.randbits(62)
    )
    return UUID(int=valor)
