"""Sessão de login e refresh token no domínio de identidade (002/T2)."""

import hashlib
import secrets
from datetime import datetime

import pytest

from src.core.errors import DomainValidationError
from src.modules.identity.domain.sessions import USER_AGENT_MAX, hash_refresh_token
from tests.factories import make_auth_session, make_refresh_token


def test_hash_do_refresh_token_e_o_sha256_em_hexadecimal() -> None:
    """002/R3.3"""
    token = secrets.token_urlsafe(32)
    assert hash_refresh_token(token) == hashlib.sha256(token.encode()).hexdigest()


@pytest.mark.parametrize(
    "valor",
    [secrets.token_urlsafe(32), "A" * 64, ""],
    ids=["token-em-claro", "maiusculas", "vazio"],
)
def test_refresh_token_so_aceita_o_hash(valor: str) -> None:
    """002/R3.3"""
    with pytest.raises(DomainValidationError):
        make_refresh_token(token_hash=valor)


def test_repr_do_refresh_token_nao_mostra_o_hash() -> None:
    """002/R3.3"""
    refresh = make_refresh_token()
    assert refresh.token_hash not in repr(refresh)


def test_datas_sem_fuso_horario_sao_recusadas() -> None:
    """002/T2"""
    sem_fuso = datetime(2026, 11, 6, 12, 0)  # noqa: DTZ001 - é o caso testado
    with pytest.raises(DomainValidationError):
        make_auth_session(created_at=sem_fuso)
    with pytest.raises(DomainValidationError):
        make_refresh_token(expires_at=sem_fuso)


def test_sessao_normaliza_o_ip_e_recusa_ip_invalido() -> None:
    """002/T2"""
    assert make_auth_session(ip="2001:DB8::0001").ip == "2001:db8::1"
    with pytest.raises(DomainValidationError):
        make_auth_session(ip="999.1.1.1")


def test_sessao_descarta_a_zona_do_ipv6() -> None:
    """002/T2: a zona (`fe80::1%eth0`) não tem limite de tamanho e estouraria a coluna `ip`."""
    assert make_auth_session(ip="fe80::1%" + "x" * 100).ip == "fe80::1"


def test_user_agent_longo_e_cortado_no_limite_da_coluna() -> None:
    """002/T2: o cabeçalho vem do cliente e não pode derrubar o login."""
    assert make_auth_session(user_agent="x" * 5000).user_agent == "x" * USER_AGENT_MAX
