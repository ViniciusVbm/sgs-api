"""Administração de atribuições (003/T7; R2.1 a R2.5)."""

from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI

from tests.integration.acesso import GLOBAL, Sessoes, bearer, eventos, id_pelo_codigo, logado

ROTA = "/api/v1/admin/atribuicoes"


async def test_admin_atribui_com_escopo_compativel_e_audita(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R2.1, R2.3, R2.4; R4.5: vale na próxima requisição do atribuído."""
    admin = await logado(sessoes, ("ADMIN_TI", GLOBAL))
    alvo = await logado(sessoes)
    area = await id_pelo_codigo(sessoes, "area", "SAUDE_MENTAL")
    antes = await cliente.get("/api/v1/me", headers=bearer(app, alvo))

    resposta = await cliente.post(
        ROTA,
        json={
            "usuario_id": str(alvo.user_id),
            "papel": "COORD_TECNICO",
            "escopo_tipo": "area",
            "escopo_id": str(area),
            "valido_ate": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
        },
        headers=bearer(app, admin),
    )
    depois = await cliente.get("/api/v1/me", headers=bearer(app, alvo))

    assert resposta.status_code == 201, resposta.text
    assert antes.json()["papeis"] == []
    assert [p["papel"] for p in depois.json()["papeis"]] == ["COORD_TECNICO"]
    [evento] = await eventos(sessoes, "papel.atribuido")
    assert evento["metadata"]["concedido_por"] == str(admin.user_id)


async def test_escopo_incompativel_ou_inexistente_e_422(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R2.1, R2.2: Gestor de Unidade exige `unidade`; distrito 999 não existe."""
    admin = bearer(app, await logado(sessoes, ("ADMIN_TI", GLOBAL)))
    alvo = await logado(sessoes)

    amplo = await cliente.post(
        ROTA,
        json={"usuario_id": str(alvo.user_id), "papel": "GESTOR_UNIDADE", "escopo_tipo": "global"},
        headers=admin,
    )
    inexistente = await cliente.post(
        ROTA,
        json={
            "usuario_id": str(alvo.user_id),
            "papel": "TECNICO_DISTRITAL",
            "escopo_tipo": "distrito",
            "escopo_id": "999",
        },
        headers=admin,
    )

    assert amplo.status_code == 422
    assert inexistente.status_code == 422


async def test_ninguem_atribui_papel_a_si_mesmo(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R2.5 (segregação de funções)."""
    admin = await logado(sessoes, ("ADMIN_TI", GLOBAL))

    resposta = await cliente.post(
        ROTA,
        json={"usuario_id": str(admin.user_id), "papel": "GESTOR_DADOS", "escopo_tipo": "global"},
        headers=bearer(app, admin),
    )

    assert resposta.status_code == 403


async def test_remover_atribuicao_audita_e_tira_a_permissao(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """R2.4; R4.5."""
    admin = bearer(app, await logado(sessoes, ("ADMIN_TI", GLOBAL)))
    alvo = await logado(sessoes)
    criada = await cliente.post(
        ROTA,
        json={"usuario_id": str(alvo.user_id), "papel": "DIRETORIA", "escopo_tipo": "global"},
        headers=admin,
    )

    removida = await cliente.delete(f"{ROTA}/{criada.json()['id']}", headers=admin)
    resumo = await cliente.get("/api/v1/dashboard/resumo", headers=bearer(app, alvo))

    assert removida.status_code == 204
    assert resumo.status_code == 403
    assert len(await eventos(sessoes, "papel.removido")) == 1


async def test_so_quem_tem_papel_assign_administra(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))

    assert (await cliente.get(ROTA, headers=gestor)).status_code == 403
    papeis = await cliente.get(
        "/api/v1/admin/papeis", headers=bearer(app, await logado(sessoes, ("ADMIN_TI", GLOBAL)))
    )
    exigidos = {p["codigo"]: p["escopo_exigido"] for p in papeis.json()}
    assert exigidos == {
        "ADMIN_TI": "global",
        "AUDITOR": "global",
        "COORD_TECNICO": "area",
        "DIRETORIA": "global",
        "GESTOR_DADOS": "global",
        "GESTOR_UNIDADE": "unidade",
        "TECNICO_DISTRITAL": "distrito",
    }
