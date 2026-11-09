"""`GET /me` (003/T6; R5.1)."""

import httpx
from fastapi import FastAPI

from tests.integration.acesso import Sessoes, bearer, id_pelo_codigo, logado


async def test_me_traz_papeis_escopos_e_permissoes(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    ds = await id_pelo_codigo(sessoes, "distrito", "DS-III")
    usuario = await logado(sessoes, ("TECNICO_DISTRITAL", ("distrito", str(ds))))

    resposta = await cliente.get("/api/v1/me", headers=bearer(app, usuario))

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert corpo["id"] == str(usuario.user_id)
    assert [(p["papel"], p["escopo_tipo"], p["escopo_id"]) for p in corpo["papeis"]] == [
        ("TECNICO_DISTRITAL", "distrito", str(ds))
    ]
    assert corpo["permissoes"]["unidade:update"] == [{"tipo": "distrito", "id": str(ds)}]
    assert corpo["permissoes"]["unidade:read"] == [{"tipo": "global", "id": None}]
    assert "unidade:deactivate" not in corpo["permissoes"]


async def test_me_sem_token_e_401(cliente: httpx.AsyncClient) -> None:
    assert (await cliente.get("/api/v1/me")).status_code == 401


async def test_me_vale_para_quem_nao_tem_papel(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    usuario = await logado(sessoes)

    resposta = await cliente.get("/api/v1/me", headers=bearer(app, usuario))

    assert resposta.status_code == 200
    assert resposta.json()["papeis"] == []
    assert resposta.json()["permissoes"] == {}
