"""Segundo fator TOTP (spec 002, R2): porta do verificador e da cifra do segredo.

O segredo TOTP é guardado cifrado com AES-256-GCM (R2.5): a porta `CifraDeCampo` é atendida pelo
`FieldCipher` do `core`, montado pela raiz de composição, porque a application não importa o
`core` (contrato do import-linter).
"""

from datetime import datetime
from typing import Protocol


class VerificadorTotp(Protocol):
    def novo_segredo(self) -> str:
        """Segredo base32 novo (R2.1)."""
        ...

    def uri(self, segredo: str, conta: str) -> str:
        """URI `otpauth://` para o QR code (R2.1)."""
        ...

    def passo_valido(self, segredo: str, codigo: str, agora: datetime) -> int | None:
        """O passo de 30 s em que o código vale, na janela de ±1 passo (R2.4); `None` se não
        vale. Quem chama recusa o passo já usado (anti-reuso, `users.mfa_last_step`)."""
        ...


class CifraDeCampo(Protocol):
    def encrypt(self, plaintext: str, *, aad: str) -> str: ...

    def decrypt(self, value: str, *, aad: str) -> str: ...
