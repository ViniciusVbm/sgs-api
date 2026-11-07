"""Tabelas do cadastro criadas pela migração 0003_access para o escopo do RBAC (spec 003).

Só o que a 003 precisa: os distritos e as áreas técnicas, níveis de escopo, e um stub de
`health_units` com o que liga a unidade ao distrito e ao tipo. A spec 006 (migração 0006) completa
estas tabelas, cria as demais do cadastro e põe as FKs.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, SmallInteger, String, Table, Uuid, func

from src.core.db import metadata


def _timestamps() -> tuple[Column[datetime], Column[datetime]]:
    return (
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column(
            "updated_at",
            DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
            onupdate=func.now(),
        ),
    )


districts = Table(
    "districts",
    metadata,
    Column("id", SmallInteger, primary_key=True, autoincrement=False),
    Column("code", String(20), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    *_timestamps(),
)

technical_areas = Table(
    "technical_areas",
    metadata,
    Column("id", SmallInteger, primary_key=True, autoincrement=False),
    Column("code", String(50), nullable=False, unique=True),
    Column("name", String(100), nullable=False),
    *_timestamps(),
)

health_units = Table(
    "health_units",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("district_id", SmallInteger, nullable=False),
    Column("unit_type_id", SmallInteger, nullable=False),
)
