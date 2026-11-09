"""`sgs-admin create-user` (002/T8): primeiro administrador, Argon2id e auditoria."""

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from src.tools.sgs_admin import criar_usuario
from tests.factories import make_settings
from tests.integration.postgres import BancoDeTeste, motor

SENHA = "senha-do-admin-123"


async def test_cria_o_admin_com_papel_e_auditoria(banco: BancoDeTeste) -> None:
    settings = make_settings(database_url=SecretStr(banco.url_api))

    usuario_id = await criar_usuario(
        banco.url_api,
        settings,
        username="Admin",
        nome="Administrador",
        email=None,
        senha=SENHA,
        papel="ADMIN_TI",
    )
    engine = motor(banco.url_api)
    async with engine.connect() as conexao:
        hash_ = await conexao.scalar(
            text("SELECT password_hash FROM users WHERE username = 'admin'")
        )
        papel = await conexao.scalar(
            text(
                "SELECT r.code FROM role_assignments a JOIN roles r ON r.id = a.role_id"
                " WHERE a.user_id = CAST(:id AS uuid)"
            ),
            {"id": usuario_id},
        )
        acoes = list(
            (
                await conexao.execute(
                    text("SELECT action, metadata::text FROM audit_log ORDER BY id")
                )
            ).all()
        )
    await engine.dispose()

    assert hash_.startswith("$argon2id$")
    assert papel == "ADMIN_TI"
    assert [a for a, _ in acoes] == ["usuario.criado", "papel.atribuido"]
    assert SENHA not in str(acoes)


async def test_usuario_repetido_e_recusado(banco: BancoDeTeste) -> None:
    settings = make_settings(database_url=SecretStr(banco.url_api))
    await criar_usuario(
        banco.url_api,
        settings,
        username="admin",
        nome="A",
        email=None,
        senha=SENHA,
        papel="ADMIN_TI",
    )

    with pytest.raises(ValueError, match="já existe"):
        await criar_usuario(
            banco.url_api,
            settings,
            username="admin",
            nome="B",
            email=None,
            senha=SENHA,
            papel="ADMIN_TI",
        )
