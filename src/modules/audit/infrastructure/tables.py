"""Tabelas da auditoria, iguais às da migração 0001_base (e o índice da 0011_03)."""

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Identity,
    Index,
    SmallInteger,
    String,
    Table,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from src.core.db import metadata

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", BigInteger, Identity(always=True), primary_key=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("actor_user_id", Uuid, nullable=True),
    Column("actor_roles", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("session_id", Uuid, nullable=True),
    Column("ip", String(64), nullable=True),
    Column("request_id", String(128), nullable=True),
    Column("action", String(100), nullable=False),
    Column("entity_type", String(50), nullable=True),
    Column("entity_id", String(100), nullable=True),
    Column("changes", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("prev_hash", CHAR(64), nullable=False),
    Column("hash", CHAR(64), nullable=False),
    UniqueConstraint("hash"),
    UniqueConstraint("prev_hash"),
)

# Histórico de uma entidade, mais recente primeiro (migração 0011_03, spec 011 R1.1).
Index(
    "ix_audit_log_entity",
    audit_log.c.entity_type,
    audit_log.c.entity_id,
    audit_log.c.occurred_at.desc(),
)

audit_chain_head = Table(
    "audit_chain_head",
    metadata,
    Column("id", SmallInteger, primary_key=True, autoincrement=False),
    Column("last_hash", CHAR(64), nullable=False),
    CheckConstraint("id = 1", name="linha_unica"),
)
