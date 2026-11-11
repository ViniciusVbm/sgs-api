"""Registro da trilha de auditoria e hash encadeado (spec 001, R5.3).

hash = SHA-256(prev_hash || conteúdo canônico), em que o conteúdo canônico é o JSON do registro
com chaves ordenadas, sem espaços, em UTF-8 e com a data em UTC. Recalcular o hash a partir do
que está gravado revela qualquer adulteração.

Spec 013 (emenda à canonicalização da 001, design § Emenda à spec 001): `actor_type`, `origin`,
`user_agent`, `result` e `result_reason` só entram no conteúdo canônico quando não são nulos. Um
registro anterior à 013 continua com o mesmo hash; anular ou preencher um desses campos depois da
gravação muda o hash.
"""

import hashlib
import ipaddress
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Self
from uuid import UUID

from src.core.errors import DomainValidationError, FieldError

GENESIS_HASH = "0" * 64

# Ações no formato recurso.verbo (steering/structure.md): unidade.atualizada, auth.login.
_ACTION = re.compile(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*")
_HASH = re.compile(r"[0-9a-f]{64}")

TIPOS_DE_ATOR = frozenset({"usuario", "anonimo", "sistema", "servico", "seed", "cli_admin"})
"""013/R1.1: quem fez a ação. Os mesmos valores do CHECK `ck_audit_log_actor_type_valido`."""
RESULTADOS = frozenset({"success", "failure", "denied"})
"""013/R4.1: resultado da operação (`ck_audit_log_result_valido`)."""
CATEGORIAS = frozenset(
    {"autenticacao", "autorizacao", "validacao", "conflito", "precondicao", "erro_interno"}
)
"""013/R4.1: por que falhou ou foi negada (`ck_audit_log_result_reason_valido`)."""
ORIGEM_MAX = 100
USER_AGENT_MAX = 200


def _freeze_json(value: Any, parents: set[int] | None = None) -> Any:
    if not isinstance(value, Mapping | list | tuple):
        return value
    parents = parents if parents is not None else set()
    identity = id(value)
    if identity in parents:
        raise _invalid("mudancas", "Os valores JSON não podem conter referências cíclicas.")
    parents.add(identity)
    try:
        if isinstance(value, Mapping):
            frozen = {key: _freeze_json(item, parents) for key, item in value.items()}
            return MappingProxyType(frozen)
        return tuple(_freeze_json(item, parents) for item in value)
    finally:
        parents.remove(identity)


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True)
class Ator:
    """Quem fez a ação e de onde. `tipo` e `origem` (013/R1.1) separam a pessoa do sistema, do
    seed e dos comandos administrativos; `user_agent` (013/R3.4) é declaração do cliente."""

    user_id: UUID | None = None
    papeis: tuple[str, ...] = ()
    session_id: UUID | None = None
    ip: str | None = None
    request_id: str | None = None
    tipo: str | None = None
    origem: str | None = None
    user_agent: str | None = None

    def __post_init__(self) -> None:
        if self.tipo is not None and self.tipo not in TIPOS_DE_ATOR:
            raise _invalid("tipo", "Tipo de ator inválido.")
        if self.tipo == "usuario" and self.user_id is None:
            raise _invalid("tipo", "Evento de usuário precisa do usuário.")
        if self.origem is not None and not 0 < len(self.origem) <= ORIGEM_MAX:
            raise _invalid("origem", f"Use de 1 a {ORIGEM_MAX} caracteres.")
        if self.user_agent is not None and len(self.user_agent) > USER_AGENT_MAX:
            raise _invalid("user_agent", f"Use até {USER_AGENT_MAX} caracteres.")
        if self.ip is not None:
            try:
                normalized = str(ipaddress.ip_address(self.ip))
            except ValueError:
                raise _invalid("ip", "IP inválido.") from None
            object.__setattr__(self, "ip", normalized)


@dataclass(frozen=True)
class Entidade:
    tipo: str
    id: str


@dataclass(frozen=True)
class Mudanca:
    """Alteração de um campo; `de` e `para` precisam ser valores JSON."""

    campo: str
    de: Any
    para: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "de", _freeze_json(self.de))
        object.__setattr__(self, "para", _freeze_json(self.para))


@dataclass(frozen=True)
class AuditEntry:
    occurred_at: datetime
    action: str
    actor: Ator
    entity: Entidade | None
    changes: tuple[Mudanca, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    prev_hash: str = GENESIS_HASH
    hash: str = ""
    result: str | None = None
    result_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "changes", tuple(self.changes))
        object.__setattr__(self, "metadata", _freeze_json(dict(self.metadata)))

    @classmethod
    def create(
        cls,
        *,
        prev_hash: str,
        occurred_at: datetime,
        action: str,
        actor: Ator,
        entity: Entidade | None = None,
        changes: tuple[Mudanca, ...] = (),
        metadata: Mapping[str, Any] | None = None,
        result: str | None = None,
        result_reason: str | None = None,
    ) -> Self:
        if occurred_at.tzinfo is None:
            raise _invalid("occurred_at", "Informe o fuso horário.")
        if len(action) > 100 or not _ACTION.fullmatch(action):
            raise _invalid("acao", "Use o formato recurso.verbo, em minúsculas.")
        if not _HASH.fullmatch(prev_hash):
            raise _invalid("prev_hash", "Hash anterior inválido.")
        _validar_resultado(result, result_reason)
        draft = cls(
            occurred_at=occurred_at.astimezone(UTC),
            action=action,
            actor=actor,
            entity=entity,
            changes=tuple(changes),
            metadata=dict(metadata or {}),
            prev_hash=prev_hash,
            result=result,
            result_reason=result_reason,
        )
        return replace(draft, hash=draft.recompute_hash())

    def content(self) -> dict[str, Any]:
        """Conteúdo coberto pelo hash, só com tipos JSON. As 13 chaves da 001 vêm sempre; as da
        013 só quando não são nulas (por isso os registros antigos mantêm o hash)."""
        conteudo: dict[str, Any] = {
            "occurred_at": self.occurred_at.astimezone(UTC).isoformat(timespec="microseconds"),
            "actor_user_id": str(self.actor.user_id) if self.actor.user_id else None,
            "actor_roles": list(self.actor.papeis),
            "session_id": str(self.actor.session_id) if self.actor.session_id else None,
            "ip": self.actor.ip,
            "request_id": self.actor.request_id,
            "action": self.action,
            "entity_type": self.entity.tipo if self.entity else None,
            "entity_id": self.entity.id if self.entity else None,
            "changes": [
                {"campo": m.campo, "de": _thaw_json(m.de), "para": _thaw_json(m.para)}
                for m in self.changes
            ],
            "metadata": _thaw_json(self.metadata),
        }
        opcionais = {
            "actor_type": self.actor.tipo,
            "origin": self.actor.origem,
            "user_agent": self.actor.user_agent,
            "result": self.result,
            "result_reason": self.result_reason,
        }
        conteudo.update({chave: valor for chave, valor in opcionais.items() if valor is not None})
        return conteudo

    def canonical_content(self) -> bytes:
        try:
            text = json.dumps(
                self.content(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
        except (TypeError, ValueError):
            raise _invalid("mudancas", "Os valores precisam ser JSON (sem NaN).") from None
        return text.encode("utf-8")

    def recompute_hash(self) -> str:
        return hashlib.sha256(self.prev_hash.encode("ascii") + self.canonical_content()).hexdigest()


def _validar_resultado(result: str | None, result_reason: str | None) -> None:
    """013/R4.1: falha e negação têm categoria; sucesso não tem."""
    if result is not None and result not in RESULTADOS:
        raise _invalid("result", "Resultado inválido.")
    if result_reason is not None and result_reason not in CATEGORIAS:
        raise _invalid("result_reason", "Categoria de resultado inválida.")
    if result in {"failure", "denied"} and result_reason is None:
        raise _invalid("result_reason", "Falha e negação precisam da categoria.")
    if result_reason is not None and result in {None, "success"}:
        raise _invalid("result_reason", "Só falha e negação têm categoria.")


def _invalid(campo: str, mensagem: str) -> DomainValidationError:
    return DomainValidationError(
        "Registro de auditoria inválido.", errors=[FieldError(campo=campo, mensagem=mensagem)]
    )
