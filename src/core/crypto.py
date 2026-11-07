"""Criptografia de campo AES-256-GCM com chaves versionadas (spec 002, R2.5).

Formato gravado: `v{versão}:{nonce_b64}:{texto_cifrado_b64}` (docs/architecture/modelo-dados.md).
O nonce tem 96 bits e é sorteado a cada gravação; o texto cifrado inclui a tag GCM de 128 bits.
A versão diz com qual chave o valor foi cifrado, o que permite trocar a chave ativa sem perder os
valores antigos.
"""

import base64
import binascii
import os
import re
from collections.abc import Mapping

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_BYTES = 32  # AES-256
NONCE_BYTES = 12  # 96 bits, o tamanho recomendado para o GCM
# Versão canônica (sem zero à esquerda) e curta, para int() nunca receber um número gigante.
_FORMAT = re.compile(r"v([1-9][0-9]{0,8}):([A-Za-z0-9+/=]+):([A-Za-z0-9+/=]+)")


class DecryptionError(Exception):
    """Valor cifrado malformado, adulterado, de outra chave ou de outro contexto (AAD)."""


class FieldCipher:
    """Cifra e decifra campos sensíveis, como o segredo TOTP.

    `aad` amarra o valor ao seu contexto (por exemplo, o `user_id` dono do segredo): um valor
    copiado para outra linha não decifra.
    """

    __slots__ = ("_active_version", "_ciphers")

    def __init__(self, keys: Mapping[int, bytes], *, active_version: int) -> None:
        for version, key in keys.items():
            if version < 1:
                raise ValueError(f"a versão de chave {version} deve ser um inteiro positivo")
            if len(key) != KEY_BYTES:
                raise ValueError(f"a chave de versão {version} deve ter {KEY_BYTES} bytes")
        if active_version not in keys:
            raise ValueError(f"não há chave para a versão ativa {active_version}")
        self._ciphers = {version: AESGCM(key) for version, key in keys.items()}
        self._active_version = active_version

    def __repr__(self) -> str:
        return f"FieldCipher(versions={sorted(self._ciphers)}, active={self._active_version})"

    def encrypt(self, plaintext: str, *, aad: str) -> str:
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = self._ciphers[self._active_version].encrypt(
            nonce, plaintext.encode(), aad.encode()
        )
        return f"v{self._active_version}:{_b64(nonce)}:{_b64(ciphertext)}"

    def decrypt(self, value: str, *, aad: str) -> str:
        # As mensagens nunca incluem o valor recebido, e `from None` descarta a causa original.
        match = _FORMAT.fullmatch(value)
        if match is None:
            raise DecryptionError("valor cifrado em formato inválido")
        version, nonce_b64, ciphertext_b64 = match.groups()
        cipher = self._ciphers.get(int(version))
        if cipher is None:
            raise DecryptionError(f"não há chave para a versão {version}")
        try:
            nonce = base64.b64decode(nonce_b64, validate=True)
            ciphertext = base64.b64decode(ciphertext_b64, validate=True)
        except binascii.Error:
            raise DecryptionError("valor cifrado em formato inválido") from None
        if len(nonce) != NONCE_BYTES:
            raise DecryptionError("valor cifrado em formato inválido")
        try:
            return cipher.decrypt(nonce, ciphertext, aad.encode()).decode()
        except InvalidTag:
            raise DecryptionError("valor cifrado adulterado ou de outro contexto") from None


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
