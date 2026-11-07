"""Portas do módulo de acesso.

Os repositórios trabalham sobre a transação de quem os usa: quem chama abre, confirma ou desfaz.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.access.domain.authorization import Concessao


class RepositorioDePermissoes(Protocol):
    async def versao(self, usuario_id: UUID) -> int | None:
        """`users.authz_version` do usuário; `None` se ele não existe."""
        ...

    async def concessoes(self, usuario_id: UUID, agora: datetime) -> Sequence[Concessao]:
        """Uma concessão por permissão de cada atribuição do usuário (direta ou de grupo) que
        não tenha expirado até `agora`."""
        ...

    async def invalidar(self, usuario_id: UUID) -> None:
        """Incrementa `users.authz_version`. Quem altera as atribuições de um usuário chama na
        mesma transação, e a mudança vale na próxima requisição (003/R4.5)."""
        ...
