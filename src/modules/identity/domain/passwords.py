"""Senhas (spec 002, R1.3 e R1.7): porta do hasher Argon2id.

A implementação (pwdlib) fica em `infrastructure/`. O domínio só conhece o formato PHC, que o
`User` confere (`ARGON2ID_PHC`).
"""

from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, senha: str) -> str:
        """Hash Argon2id no formato PHC."""
        ...

    def verificar(self, senha: str, hash_: str) -> bool:
        """Se a senha confere com o hash. Nunca levanta por senha errada."""
        ...

    def verificar_ficticio(self, senha: str) -> None:
        """Gasta o mesmo tempo de uma verificação real, para usuário inexistente (R1.3)."""
        ...
