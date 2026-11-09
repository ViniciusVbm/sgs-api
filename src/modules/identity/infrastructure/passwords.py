"""`PasswordHasher` Argon2id com pwdlib (spec 002, R1.3 e R1.7; design § Componentes)."""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher


class Argon2PasswordHasher:
    """Parâmetros padrão do pwdlib (Argon2id, RFC 9106). O hash fictício é calculado uma vez, para
    a verificação de usuário inexistente custar o mesmo que a de um real (R1.3)."""

    def __init__(self) -> None:
        self._hasher = PasswordHash((Argon2Hasher(),))
        self._ficticio = self._hasher.hash("senha-ficticia-para-tempo-constante")

    def hash(self, senha: str) -> str:
        return self._hasher.hash(senha)

    def verificar(self, senha: str, hash_: str) -> bool:
        try:
            return self._hasher.verify(senha, hash_)
        except Exception:  # hash mal formado nunca autentica
            return False

    def verificar_ficticio(self, senha: str) -> None:
        self._hasher.verify(senha, self._ficticio)
