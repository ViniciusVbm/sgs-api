"""Repositório do RBAC sobre a sessão SQLAlchemy de quem o usa (SQLAlchemy Core)."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import Integer, Uuid, column, or_, select, table, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.access.domain.authorization import Concessao, escopo_de
from src.modules.access.infrastructure.tables import permissions, role_assignments, role_permissions

# Só a coluna de versão de `users` (spec 002); a tabela completa é da infraestrutura de identity.
_users = table("users", column("id", Uuid), column("authz_version", Integer))


class SqlRepositorioDePermissoes:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def versao(self, usuario_id: UUID) -> int | None:
        return await self._session.scalar(
            select(_users.c.authz_version).where(_users.c.id == usuario_id)
        )

    async def concessoes(self, usuario_id: UUID, agora: datetime) -> Sequence[Concessao]:
        vigente = or_(
            role_assignments.c.valid_until.is_(None), role_assignments.c.valid_until > agora
        )
        resultado = await self._session.execute(
            select(
                permissions.c.code,
                role_permissions.c.max_scope,
                role_assignments.c.scope_type,
                role_assignments.c.scope_id,
                role_assignments.c.valid_until,
            )
            .select_from(
                role_assignments.join(
                    role_permissions, role_permissions.c.role_id == role_assignments.c.role_id
                ).join(permissions, permissions.c.id == role_permissions.c.permission_id)
            )
            .where(role_assignments.c.user_id == usuario_id, vigente)
        )
        return [
            Concessao(
                permissao=codigo,
                escopo_maximo=escopo_maximo,
                escopo=escopo_de(nivel, id_do_escopo),
                valido_ate=valido_ate,
            )
            for codigo, escopo_maximo, nivel, id_do_escopo, valido_ate in resultado.all()
        ]

    async def invalidar(self, usuario_id: UUID) -> None:
        await self._session.execute(
            update(_users)
            .where(_users.c.id == usuario_id)
            .values(authz_version=_users.c.authz_version + 1)
        )
