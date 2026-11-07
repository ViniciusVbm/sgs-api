"""Escopos e verificação de permissão (spec 003, design § Resolução de permissões e § Verificação).

Função pura, sem banco: quem chama já resolveu as permissões efetivas do usuário e os atributos
de escopo do recurso.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Global:
    """Vale para qualquer recurso."""


@dataclass(frozen=True, slots=True)
class Area:
    """Uma área técnica (`technical_areas.id`)."""

    id: int


@dataclass(frozen=True, slots=True)
class Distrito:
    """Um distrito sanitário (`districts.id`)."""

    id: int


@dataclass(frozen=True, slots=True)
class Unidade:
    """Uma unidade de saúde (`health_units.id`)."""

    id: UUID


type Escopo = Global | Area | Distrito | Unidade

type PermissoesEfetivas = Mapping[str, Sequence[Escopo]]
"""Código da permissão (`recurso:acao`) → escopos em que o usuário a tem."""


@dataclass(frozen=True, slots=True)
class Alvo:
    """Atributos de escopo do recurso verificado: a unidade, o distrito e a área técnica dela."""

    unidade_id: UUID
    distrito_id: int
    area_id: int


def pode(perms: PermissoesEfetivas, perm: str, alvo: Alvo | None = None) -> bool:
    """Diz se o usuário tem `perm` e, havendo alvo, se algum dos seus escopos o cobre.

    Sem alvo (R4.2), basta ter a permissão em algum escopo. Com alvo (R4.3), autoriza se houver
    um escopo `Global`, ou `Area` igual à área da unidade, ou `Distrito` igual ao distrito, ou
    `Unidade` igual à própria unidade. Permissão ausente nega (deny by default).
    """
    escopos = perms.get(perm, ())
    if alvo is None:
        return bool(escopos)
    return any(_cobre(escopo, alvo) for escopo in escopos)


def _cobre(escopo: Escopo, alvo: Alvo) -> bool:
    match escopo:
        case Global():
            return True
        case Area(id=area_id):
            return area_id == alvo.area_id
        case Distrito(id=distrito_id):
            return distrito_id == alvo.distrito_id
        case Unidade(id=unidade_id):
            return unidade_id == alvo.unidade_id
