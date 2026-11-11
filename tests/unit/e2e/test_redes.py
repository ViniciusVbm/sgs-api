"""Escolha da subnet de borda das suítes e2e, sem Docker (spec 013, T4; R3.7)."""

import ipaddress

import pytest

from tests.e2e.redes import FAIXA_DO_PROJETO, POOLS_DO_DOCKER, SUBNETS, SubnetOcupadaError, escolher


def test_subnet_ocupada_usa_alternativa_ou_para_com_mensagem() -> None:
    """013/R3.7: subnet livre → proxy no último endereço útil; ocupada → para dizendo a rede e
    a variável; com a variável, usa a alternativa."""
    livre = escolher("AUDITORIA", [("sgs-local_default", "172.19.0.0/16")], {})
    assert (livre.subnet, livre.proxy_ip, livre.gateway_ip) == (
        "10.231.13.0/28",
        "10.231.13.14",
        "10.231.13.1",
    )
    assert livre.ambiente() == {
        "SGS_BORDA_SUBNET": "10.231.13.0/28",
        "SGS_BORDA_PROXY_IP": "10.231.13.14",
    }

    ocupada = [("outro_projeto_borda", "10.231.13.0/24")]
    with pytest.raises(SubnetOcupadaError, match=r"outro_projeto_borda.*SGS_E2E_SUBNET_AUDITORIA"):
        escolher("AUDITORIA", ocupada, {})

    alternativa = escolher("AUDITORIA", ocupada, {"SGS_E2E_SUBNET_AUDITORIA": "10.231.40.0/28"})
    assert alternativa.proxy_ip == "10.231.40.14"


def test_subnets_padrao_sao_unicas_na_faixa_e_fora_dos_pools_do_docker() -> None:
    """013/R3.7"""
    redes = [ipaddress.IPv4Network(s) for s in SUBNETS.values()]

    assert all(r.subnet_of(FAIXA_DO_PROJETO) for r in redes)
    assert not any(r.overlaps(p) for r in redes for p in POOLS_DO_DOCKER)
    assert not any(a.overlaps(b) for i, a in enumerate(redes) for b in redes[i + 1 :])
