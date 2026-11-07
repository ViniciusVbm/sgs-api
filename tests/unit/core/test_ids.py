"""UUID v7 com a biblioteca padrão (002/T2; steering/tech.md: IDs são UUID v7)."""

import time
import uuid

import pytest

from src.core.ids import uuid7


def test_uuid7_tem_versao_7_e_variante_rfc() -> None:
    """002/T2"""
    gerado = uuid7()
    assert gerado.version == 7
    assert gerado.variant == uuid.RFC_4122


def test_uuid7_comeca_pelos_milissegundos_unix() -> None:
    """002/T2"""
    antes = time.time_ns() // 1_000_000
    gerado = uuid7()
    depois = time.time_ns() // 1_000_000
    assert antes <= gerado.int >> 80 <= depois


def test_uuid7_ordena_pela_hora_de_criacao() -> None:
    """002/T2"""
    assert uuid7(unix_ms=1_000) < uuid7(unix_ms=1_001)


def test_uuid7_nao_se_repete_no_mesmo_milissegundo() -> None:
    """002/T2"""
    assert len({uuid7(unix_ms=1_000) for _ in range(1_000)}) == 1_000


@pytest.mark.parametrize("unix_ms", [-1, 1 << 48])
def test_uuid7_recusa_instante_fora_dos_48_bits(unix_ms: int) -> None:
    """002/T2"""
    with pytest.raises(ValueError, match="48 bits"):
        uuid7(unix_ms=unix_ms)
