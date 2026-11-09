"""Roteiro de aceitação do MVP (Entrega 11; docs/integration-audit/09-plano-testes.md).

De ponta a ponta, num banco migrado e com a massa de demonstração: o primeiro administrador é
criado pelo `sgs-admin`, os usuários entram com senha e TOTP como no front, e cada passo confere
um critério da spec. Roda com `make test-all` (precisa de Docker para o PostgreSQL).
"""

from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import SecretStr

from src.tools.seed_demo import carregar
from src.tools.sgs_admin import criar_usuario
from tests.factories import make_settings
from tests.integration.identity.autenticacao import ORIGEM, cadastrar_e_entrar
from tests.integration.postgres import BancoDeTeste

SENHA_DEMO = "senha-demo-aceitacao-123"


async def _entrar(cliente: httpx.AsyncClient, username: str) -> dict[str, str]:
    confirmado, _ = await cadastrar_e_entrar(cliente, username, SENHA_DEMO)
    assert confirmado.status_code == 200, confirmado.text
    return {"Authorization": f"Bearer {confirmado.json()['access_token']}"}


async def test_roteiro_do_mvp(
    banco: BancoDeTeste, app: FastAPI, cliente: httpx.AsyncClient
) -> None:
    settings = make_settings(database_url=SecretStr(banco.url_api))

    # 1. Saúde da API.
    assert (await cliente.get("/health/live")).status_code == 200

    # 2. Massa de demonstração (010) e primeiro administrador (002/T8).
    await carregar(banco.url_api, settings, senha=SENHA_DEMO)
    gestor = await _entrar(cliente, "demo.carla.dias")  # GESTOR_DADOS
    auditor = await _entrar(cliente, "demo.cecilia.gil")  # AUDITOR
    distrital = await _entrar(cliente, "demo.karina.lopes")  # TECNICO_DISTRITAL (DS-I)
    await criar_usuario(
        banco.url_api,
        settings,
        username="admin.ti",
        nome="Administrador",
        email=None,
        senha="senha-do-admin-123",
        papel="ADMIN_TI",
    )

    # 3. Sem token: 401 em qualquer rota de negócio (003/R4.1).
    assert (await cliente.get("/api/v1/unidades")).status_code == 401

    # 4. /me coerente com o perfil (003/R5.1).
    me = (await cliente.get("/api/v1/me", headers=gestor)).json()
    assert [p["papel"] for p in me["papeis"]] == ["GESTOR_DADOS"]

    # 5. Listagem com 30 unidades ou mais e busca sem acento (006/R2).
    lista = (await cliente.get("/api/v1/unidades", params={"tamanho": 100}, headers=gestor)).json()
    assert lista["total"] >= 30
    busca = await cliente.get("/api/v1/unidades", params={"q": "varzea"}, headers=gestor)
    assert [u["nome"] for u in busca.json()["itens"]] == ["Policlínica da Várzea"]
    varzea: dict[str, Any] = busca.json()["itens"][0]

    # 6. Atualização com If-Match e histórico com autor e papel (006/R3; 008/R1).
    patch = await cliente.patch(
        f"/api/v1/unidades/{varzea['id']}",
        json={"telefone": "(81) 3355-9999"},
        headers=gestor | {"If-Match": f'"{varzea["versao"]}"'},
    )
    assert patch.status_code == 200
    historico = await cliente.get(f"/api/v1/unidades/{varzea['id']}/historico", headers=gestor)
    ultimo = historico.json()["itens"][0]
    assert ultimo["acao"] == "unidade.atualizada"
    assert ultimo["autor"]["papeis"] == ["GESTOR_DADOS"]

    # 7. Remover o equipamento mantém o serviço, sem vínculo (011/R9.1, SET NULL).
    detalhe = (await cliente.get(f"/api/v1/unidades/{varzea['id']}", headers=gestor)).json()
    maternidade = next(e for e in detalhe["equipamentos"] if e["nome"] == "Maternidade da Várzea")
    removido = await cliente.delete(
        f"/api/v1/unidades/{varzea['id']}/equipamentos/{maternidade['id']}", headers=gestor
    )
    assert removido.status_code == 204
    servicos = (
        await cliente.get(f"/api/v1/unidades/{varzea['id']}/servicos", headers=gestor)
    ).json()
    assert all(s["equipamento_id"] is None for s in servicos)

    # 8. Desativação pela procedure, situação cadastral no inventário (011/R5.3, R6).
    desativada = await cliente.post(
        f"/api/v1/unidades/{varzea['id']}/desativar", json={"motivo": "Teste"}, headers=gestor
    )
    assert desativada.json()["status"] == "inativa"
    inventario = await cliente.get(
        "/api/v1/dashboard/inventario", params={"situacao": "inativa"}, headers=gestor
    )
    assert varzea["id"] in {u["unit_id"] for u in inventario.json()["itens"]}

    # 9. Catálogo e consultas da disciplina (011/R2, R3; 009).
    catalogo = (await cliente.get("/api/v1/dashboard/consultas", headers=gestor)).json()
    assert len(catalogo) == 13
    acima = await cliente.get(
        "/api/v1/dashboard/consultas/distritos-sem-cnes-acima-da-rede", headers=gestor
    )
    assert acima.json()["itens"]
    resumo = (await cliente.get("/api/v1/dashboard/resumo", headers=gestor)).json()
    assert resumo["unidades"]["total"] >= 30
    assert resumo["qualidade"]["unidades_com_pendencias"] >= 1

    # 10. Escopo por papel: o técnico do DS-I só vê o DS-I (011/T22).
    do_distrito = (await cliente.get("/api/v1/dashboard/resumo", headers=distrital)).json()
    assert len(do_distrito["unidades"]["por_distrito"]) == 1

    # 11. Auditor não altera dados; a negação é auditada (003/R4.6).
    negado = await cliente.post("/api/v1/unidades", json={}, headers=auditor)
    assert negado.status_code == 403
    eventos = await cliente.get(
        "/api/v1/auditoria/eventos", params={"acao": "acesso."}, headers=auditor
    )
    assert eventos.json()["total"] >= 1

    # 12. Cadeia de hash íntegra (008/R3.1).
    verificacao = (
        await cliente.post("/api/v1/auditoria/verificar", json={}, headers=auditor)
    ).json()
    assert verificacao["integra"] is True
    assert verificacao["verificados"] > 100

    # 13. Refresh com anti-CSRF e logout (002/R3).
    renovado = await cliente.post(
        "/api/v1/auth/refresh", headers={"X-Requested-With": "sgs", "Origin": ORIGEM}
    )
    assert renovado.status_code == 200
    novo = {"Authorization": f"Bearer {renovado.json()['access_token']}"}
    assert (await cliente.post("/api/v1/auth/logout", headers=novo)).status_code == 204
    assert (await cliente.get("/api/v1/me", headers=novo)).status_code == 401
