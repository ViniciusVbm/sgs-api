"""Fuso de Recife para as respostas da API (spec 008, design § Fuso).

Recife não tem horário de verão desde 2019, então o fuso é o deslocamento fixo de -03:00. Fixo,
e não `ZoneInfo("America/Recife")`, porque a imagem `python:3.13-slim` pode não trazer a base de
fusos do sistema; o resultado é o mesmo. O banco guarda tudo em UTC.
"""

from datetime import UTC, datetime, timedelta, timezone

RECIFE = timezone(timedelta(hours=-3), "America/Recife")


def em_recife(instante: datetime) -> datetime:
    """O instante no fuso de Recife (um instante sem fuso é tratado como UTC)."""
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    return instante.astimezone(RECIFE)


def agora_em_recife() -> datetime:
    return datetime.now(RECIFE)
