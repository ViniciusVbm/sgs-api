"""Portas do módulo de acesso.

Os repositórios trabalham sobre a transação de quem os usa: quem chama abre, confirma ou desfaz.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.modules.access.domain.atribuicoes import Atribuicao, DadosDoUsuario, Papel
from src.modules.access.domain.authorization import Alvo, Concessao


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


class ResolvedorDeAlvo(Protocol):
    """Acha os atributos de escopo de um tipo de recurso (design § Verificação, `ResourceRef`).

    Uma implementação por tipo, registrada pela raiz de composição em
    `app.state.resolvedores_de_alvo`; a unidade, por exemplo, dá o próprio id, o distrito e a
    área técnica do seu tipo.
    """

    async def alvo(self, id_do_recurso: str) -> Alvo | None:
        """`None` se o recurso não existe. O id chega em texto, como veio no caminho; um id fora
        do formato do recurso também é `None`."""
        ...


class RepositorioDeAtribuicoes(Protocol):
    """Papéis, atribuições e dados básicos do usuário (spec 003, R2 e R5)."""

    async def papeis(self) -> Sequence[Papel]: ...

    async def papel(self, codigo: str) -> Papel | None: ...

    async def usuario(self, usuario_id: UUID) -> DadosDoUsuario | None: ...

    async def atribuicoes(self, usuario_id: UUID | None, agora: datetime) -> Sequence[Atribuicao]:
        """As vigentes do usuário; com `None`, de todos."""
        ...

    async def atribuicao(self, id_: UUID) -> Atribuicao | None: ...

    async def escopo_existe(self, nivel: str, id_do_escopo: str) -> bool: ...

    async def inserir(self, atribuicao: Atribuicao) -> None: ...

    async def remover(self, id_: UUID) -> None: ...
