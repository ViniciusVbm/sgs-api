"""Usuário do domínio de identidade (002/T2; porte do `usuario` do PR #5)."""

import pytest

from src.core.errors import DomainValidationError
from src.modules.identity.domain.users import UserSource
from tests.factories import ARGON2ID_DE_TESTE, HASH_BCRYPT, make_user

DN = "uid=maria.silva,ou=pessoas,dc=recife,dc=pe,dc=gov,dc=br"


def _campos_com_erro(erro: pytest.ExceptionInfo[DomainValidationError]) -> set[str]:
    return {problema.campo for problema in erro.value.errors}


def test_usuario_local_guarda_o_hash_argon2id() -> None:
    """002/R1.7"""
    assert make_user().password_hash == ARGON2ID_DE_TESTE


@pytest.mark.parametrize(
    "senha",
    ["senha-em-texto-puro", HASH_BCRYPT, "$argon2id$sem-o-formato-phc", ARGON2ID_DE_TESTE + "\n"],
    ids=["texto-puro", "bcrypt", "prefixo-sem-formato", "quebra-de-linha"],
)
def test_usuario_local_recusa_senha_que_nao_e_hash_argon2id(senha: str) -> None:
    """002/R1.7"""
    with pytest.raises(DomainValidationError) as erro:
        make_user(password_hash=senha)
    assert _campos_com_erro(erro) == {"password_hash"}


def test_usuario_local_exige_o_hash_da_senha() -> None:
    """002/R1.7"""
    with pytest.raises(DomainValidationError) as erro:
        make_user(password_hash=None)
    assert _campos_com_erro(erro) == {"password_hash"}


def test_repr_do_usuario_nao_mostra_o_hash() -> None:
    """002/R1.7: um usuário que vá parar num log não leva o hash junto."""
    assert ARGON2ID_DE_TESTE not in repr(make_user())


@pytest.mark.parametrize("origem", [UserSource.LDAP, UserSource.OIDC])
def test_usuario_de_diretorio_tem_identificador_externo_e_nenhuma_senha(
    origem: UserSource,
) -> None:
    """002/T2"""
    usuario = make_user(source=origem, password_hash=None, external_id=DN)
    assert (usuario.password_hash, usuario.external_id) == (None, DN)

    with pytest.raises(DomainValidationError) as erro:
        make_user(source=origem, password_hash=ARGON2ID_DE_TESTE, external_id=None)
    assert _campos_com_erro(erro) == {"password_hash", "external_id"}


def test_usuario_local_nao_tem_identificador_externo() -> None:
    """002/T2"""
    with pytest.raises(DomainValidationError) as erro:
        make_user(external_id=DN)
    assert _campos_com_erro(erro) == {"external_id"}


def test_nome_de_usuario_fica_em_minusculas_e_sem_espacos_nas_pontas() -> None:
    """002/T2"""
    assert make_user(username="  Maria.Silva ").username == "maria.silva"


@pytest.mark.parametrize("campo", ["username", "display_name"])
def test_usuario_recusa_nome_vazio(campo: str) -> None:
    """002/T2"""
    with pytest.raises(DomainValidationError) as erro:
        make_user(**{campo: "   "})
    assert _campos_com_erro(erro) == {campo}


def test_email_fica_em_minusculas_e_sem_espacos_nas_pontas() -> None:
    """002/T2: a unicidade do e-mail não pode depender de maiúsculas."""
    assert make_user(email=" Maria.Silva@Example.ORG ").email == "maria.silva@example.org"


@pytest.mark.parametrize("email", ["invalido", "teste@", "@saude.pe", "teste@.com"])
def test_usuario_recusa_email_invalido(email: str) -> None:
    """002/T2"""
    with pytest.raises(DomainValidationError) as erro:
        make_user(email=email)
    assert _campos_com_erro(erro) == {"email"}
