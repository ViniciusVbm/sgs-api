"""Verificador TOTP com pyotp (spec 002, R2; design § Componentes)."""

from datetime import datetime

import pyotp

EMISSOR = "SGS Recife"
PASSO = 30  # segundos (RFC 6238)


class PyotpVerificador:
    def novo_segredo(self) -> str:
        return pyotp.random_base32()

    def uri(self, segredo: str, conta: str) -> str:
        return pyotp.TOTP(segredo, interval=PASSO).provisioning_uri(name=conta, issuer_name=EMISSOR)

    def passo_valido(self, segredo: str, codigo: str, agora: datetime) -> int | None:
        """Confere o código no passo atual e nos vizinhos (±30 s, R2.4) e devolve o passo."""
        if not (codigo.isdigit() and len(codigo) == 6):
            return None
        totp = pyotp.TOTP(segredo, interval=PASSO)
        atual = int(agora.timestamp()) // PASSO
        for passo in (atual - 1, atual, atual + 1):
            if pyotp.utils.strings_equal(totp.generate_otp(passo), codigo):
                return passo
        return None
