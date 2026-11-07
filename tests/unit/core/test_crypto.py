"""Criptografia de campo AES-256-GCM com chaves versionadas (spec 002, R2.5)."""

import base64
import os
from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.core.crypto import DecryptionError, FieldCipher

CHAVE_1 = os.urandom(32)
CHAVE_2 = os.urandom(32)
SEGREDO = "JBSWY3DPEHPK3PXP"
USUARIO = "0192f3c4-5d6e-7f80-9a1b-2c3d4e5f6a7b"


def cifrador(chaves: dict[int, bytes] | None = None, ativa: int = 1) -> FieldCipher:
    return FieldCipher(chaves or {1: CHAVE_1}, active_version=ativa)


def partes(valor: str) -> tuple[str, bytes, bytes]:
    versao, nonce, texto_cifrado = valor.split(":")
    return versao, base64.b64decode(nonce), base64.b64decode(texto_cifrado)


def test_decifra_o_valor_que_cifrou() -> None:
    """002/R2.5"""
    valor = cifrador().encrypt(SEGREDO, aad=USUARIO)

    assert cifrador().decrypt(valor, aad=USUARIO) == SEGREDO


@given(texto=st.text(), aad=st.text())
def test_decifra_qualquer_texto_com_qualquer_aad(texto: str, aad: str) -> None:
    """002/R2.5"""
    assert cifrador().decrypt(cifrador().encrypt(texto, aad=aad), aad=aad) == texto


def test_grava_versao_da_chave_nonce_de_96_bits_e_texto_cifrado_com_tag() -> None:
    """002/R2.5 (formato de docs/architecture/modelo-dados.md: v{versão}:{nonce}:{texto})"""
    versao, nonce, texto_cifrado = partes(cifrador().encrypt(SEGREDO, aad=USUARIO))

    assert versao == "v1"
    assert len(nonce) == 12
    assert len(texto_cifrado) == len(SEGREDO.encode()) + 16  # tag GCM de 128 bits
    assert SEGREDO.encode() not in texto_cifrado


def test_usa_um_nonce_novo_a_cada_gravacao() -> None:
    """002/R2.5"""
    valores = [cifrador().encrypt(SEGREDO, aad=USUARIO) for _ in range(1000)]

    assert len({partes(valor)[1] for valor in valores}) == len(valores)


def test_troca_de_chave_cifra_com_a_ativa_e_ainda_decifra_valores_antigos() -> None:
    """002/R2.5"""
    antigo = cifrador({1: CHAVE_1}, ativa=1).encrypt(SEGREDO, aad=USUARIO)
    depois_da_troca = cifrador({1: CHAVE_1, 2: CHAVE_2}, ativa=2)

    novo = depois_da_troca.encrypt(SEGREDO, aad=USUARIO)

    assert novo.startswith("v2:")
    assert depois_da_troca.decrypt(antigo, aad=USUARIO) == SEGREDO
    assert depois_da_troca.decrypt(novo, aad=USUARIO) == SEGREDO


def test_recusa_valor_de_chave_que_nao_esta_configurada() -> None:
    """002/R2.5"""
    novo = cifrador({1: CHAVE_1, 2: CHAVE_2}, ativa=2).encrypt(SEGREDO, aad=USUARIO)

    with pytest.raises(DecryptionError):
        cifrador({1: CHAVE_1}).decrypt(novo, aad=USUARIO)


def test_recusa_valor_cifrado_para_outro_usuario() -> None:
    """002/R2.5 (AAD = user_id: o valor de uma linha não serve em outra)"""
    valor = cifrador().encrypt(SEGREDO, aad=USUARIO)

    with pytest.raises(DecryptionError):
        cifrador().decrypt(valor, aad="0192f3c4-0000-7000-8000-000000000000")


def test_recusa_valor_cifrado_com_outra_chave_de_mesma_versao() -> None:
    """002/R2.5"""
    valor = cifrador({1: CHAVE_1}).encrypt(SEGREDO, aad=USUARIO)

    with pytest.raises(DecryptionError):
        cifrador({1: CHAVE_2}).decrypt(valor, aad=USUARIO)


def montar(versao: str, nonce: bytes, texto_cifrado: bytes) -> str:
    return f"{versao}:{base64.b64encode(nonce).decode()}:{base64.b64encode(texto_cifrado).decode()}"


def _inverter_um_bit(dados: bytes) -> bytes:
    return bytes([dados[0] ^ 1]) + dados[1:]


def _adulterar_texto_cifrado(valor: str) -> str:
    versao, nonce, texto_cifrado = partes(valor)
    return montar(versao, nonce, _inverter_um_bit(texto_cifrado))


def _adulterar_nonce(valor: str) -> str:
    versao, nonce, texto_cifrado = partes(valor)
    return montar(versao, _inverter_um_bit(nonce), texto_cifrado)


def _encurtar_nonce(valor: str) -> str:
    versao, nonce, texto_cifrado = partes(valor)
    return montar(versao, nonce[:8], texto_cifrado)


@pytest.mark.parametrize(
    "adulterar",
    [
        _adulterar_texto_cifrado,
        _adulterar_nonce,
        _encurtar_nonce,
        lambda valor: valor.replace("v1:", "v9:"),
        lambda valor: valor.replace("v1:", "x1:"),
        lambda valor: valor.replace("v1:", "v:"),
        lambda valor: valor.replace("v1:", "v01:"),
        lambda valor: valor[:-4],
        lambda valor: valor[:-1],
        lambda valor: valor + ":extra",
        lambda valor: valor.rsplit(":", 1)[0] + ":não-é-base64",
        lambda _: "",
        lambda _: "texto puro",
    ],
    ids=[
        "texto-cifrado-adulterado",
        "nonce-adulterado",
        "nonce-curto",
        "versao-desconhecida",
        "prefixo-errado",
        "versao-vazia",
        "versao-com-zero-a-esquerda",
        "texto-cifrado-truncado",
        "base64-com-padding-invalido",
        "parte-a-mais",
        "base64-invalido",
        "vazio",
        "texto-puro",
    ],
)
def test_recusa_valor_adulterado_ou_malformado_sem_expor_o_valor(
    adulterar: Callable[[str], str],
) -> None:
    """002/R2.5"""
    valor = adulterar(cifrador().encrypt(SEGREDO, aad=USUARIO))

    with pytest.raises(DecryptionError) as erro:
        cifrador().decrypt(valor, aad=USUARIO)

    if valor:
        assert valor not in str(erro.value)
    # A exceção original (InvalidTag, binascii.Error) não aparece no traceback do log.
    assert erro.value.__cause__ is None
    assert erro.value.__suppress_context__ or erro.value.__context__ is None


@pytest.mark.parametrize("tamanho", [0, 16, 24, 31, 33])
def test_recusa_chave_que_nao_tem_256_bits(tamanho: int) -> None:
    """002/R2.5 (AES-256 exige chave de 32 bytes)"""
    with pytest.raises(ValueError, match="32 bytes"):
        FieldCipher({1: os.urandom(tamanho)}, active_version=1)


def test_recusa_versao_ativa_sem_chave() -> None:
    """002/R2.5"""
    with pytest.raises(ValueError, match="versão ativa 2"):
        FieldCipher({1: CHAVE_1}, active_version=2)


@pytest.mark.parametrize("versao", [0, -1])
def test_recusa_versao_de_chave_que_nao_e_positiva(versao: int) -> None:
    """002/R2.5"""
    with pytest.raises(ValueError, match="inteiro positivo"):
        FieldCipher({versao: CHAVE_1, 1: CHAVE_2}, active_version=1)


def test_nao_expoe_as_chaves_na_representacao() -> None:
    """002/R2.5 (steering/security.md: nenhum segredo em log)"""
    representacao = repr(cifrador({1: CHAVE_1, 2: CHAVE_2}, ativa=2))

    for chave in (CHAVE_1, CHAVE_2):
        assert repr(chave) not in representacao
        assert base64.b64encode(chave).decode() not in representacao
        assert chave.hex() not in representacao
