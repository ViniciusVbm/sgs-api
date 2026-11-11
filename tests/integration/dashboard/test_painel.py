"""Consultas do catálogo, inventário, resumo e escopo por papel (011/T12, T13, T19, T22; 009).

Os dados entram pela API: três unidades em dois distritos, uma sem CNES, equipamentos e
serviços (um fora do CNES), e uma alteração, para o histórico ter eventos.
"""

from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from tests.integration.acesso import GLOBAL, Sessoes, bearer, id_pelo_codigo, logado

PAINEL = "/api/v1/dashboard"


@pytest.fixture
async def rede(app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes) -> dict[str, Any]:
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    ds1 = await id_pelo_codigo(sessoes, "distrito", "DS-I")
    ds2 = await id_pelo_codigo(sessoes, "distrito", "DS-II")
    caps = await id_pelo_codigo(sessoes, "tipo_unidade", "CAPS_II")
    tipos = (await cliente.get("/api/v1/referencias/tipos-servico", headers=gestor)).json()
    farmacia = next(t["id"] for t in tipos if t["codigo"] == "FARMACIA")

    async def unidade(nome: str, distrito: int, cnes: str | None) -> str:
        corpo = {
            "nome": nome,
            "tipo_unidade_id": caps,
            "distrito_id": distrito,
            "cep": "50010100",
            "endereco": "Rua A, 1",
            "status": "ativa",
            "cnes": cnes,
        }
        resposta = await cliente.post("/api/v1/unidades", json=corpo, headers=gestor)
        assert resposta.status_code == 201, resposta.text
        return str(resposta.json()["id"])

    a = await unidade("CAPS A", ds1, "1111111")
    b = await unidade("CAPS B", ds1, "2222222")
    c = await unidade("CAPS C", ds2, None)
    await cliente.post(
        f"/api/v1/unidades/{a}/equipamentos",
        json={"nome": "Policlínica", "tipo_codigo": "POLICLINICA", "quantidade": 2},
        headers=gestor,
    )
    await cliente.post(
        f"/api/v1/unidades/{a}/servicos",
        json={"nome": "Farmácia", "tipo_servico_id": farmacia, "no_cnes": False},
        headers=gestor,
    )
    await cliente.post(
        f"/api/v1/unidades/{b}/servicos",
        json={"nome": "Farmácia B", "tipo_servico_id": farmacia, "no_cnes": True},
        headers=gestor,
    )
    return {"gestor": gestor, "a": a, "b": b, "c": c, "ds1": ds1, "ds2": ds2}


async def test_subconsulta_distritos_sem_cnes_acima_da_rede(
    cliente: httpx.AsyncClient, rede: dict[str, Any]
) -> None:
    """011/R2.3: DS-II (100% sem CNES) passa da rede (1 de 3 = 33,33%); DS-I (0%) não."""
    resposta = await cliente.get(
        f"{PAINEL}/consultas/distritos-sem-cnes-acima-da-rede", headers=rede["gestor"]
    )

    assert resposta.status_code == 200
    [linha] = resposta.json()["itens"]
    assert linha["district_id"] == rede["ds2"]
    assert linha["percent_without_cnes"] == 100.0
    assert linha["network_percent_without_cnes"] == 33.33


async def test_subconsulta_unidades_com_servico_fora_do_cnes(
    cliente: httpx.AsyncClient, rede: dict[str, Any]
) -> None:
    """011/R2.4: só a unidade A tem serviço com `no_cnes` falso."""
    resposta = await cliente.get(
        f"{PAINEL}/consultas/unidades-com-servico-fora-do-cnes", headers=rede["gestor"]
    )

    assert [u["unit_id"] for u in resposta.json()["itens"]] == [rede["a"]]
    assert resposta.json()["itens"][0]["services_outside_cnes_count"] == 1


async def test_inventario_pela_view_sem_dado_pessoal(
    cliente: httpx.AsyncClient, rede: dict[str, Any]
) -> None:
    """011/R4.1 a R4.3: contagens e situação cadastral; filtro por situação."""
    todos = await cliente.get(f"{PAINEL}/inventario", headers=rede["gestor"])
    sem_cnes = await cliente.get(
        f"{PAINEL}/inventario", params={"situacao": "sem_cnes"}, headers=rede["gestor"]
    )

    assert todos.json()["total"] == 3
    a = next(u for u in todos.json()["itens"] if u["unit_id"] == rede["a"])
    assert (a["equipment_count"], a["service_count"], a["services_outside_cnes_count"]) == (1, 1, 1)
    assert "manager_name" not in a
    assert [u["unit_id"] for u in sem_cnes.json()["itens"]] == [rede["c"]]


async def test_quatro_consultas_da_etapa_3(
    cliente: httpx.AsyncClient, rede: dict[str, Any]
) -> None:
    """009/R2.1 a R2.4 (consultas da 003 reescritas)."""
    cabecalho = rede["gestor"]
    categorias = await cliente.get(f"{PAINEL}/consultas/unidades-por-categoria", headers=cabecalho)
    equipamentos = await cliente.get(
        f"{PAINEL}/consultas/equipamentos-por-tipo-e-distrito", headers=cabecalho
    )
    periodo = await cliente.get(f"{PAINEL}/consultas/alteracoes-por-periodo", headers=cabecalho)
    recentes = await cliente.get(f"{PAINEL}/consultas/alteracoes-recentes", headers=cabecalho)

    por_categoria = {(c["categoria"], c["chave"]): c["quantidade"] for c in categorias.json()}
    assert por_categoria[("status", "ativa")] == 3
    assert por_categoria[("sem_cnes", "sem_cnes")] == 1
    assert por_categoria[("distrito", str(rede["ds1"]))] == 2
    [linha] = equipamentos.json()
    assert (linha["equipment_type_code"], linha["total_quantity"]) == ("POLICLINICA", 2)
    assert sum(d["last_30_days"] for d in periodo.json()) >= 6  # 3 criações e 3 vínculos
    assert 1 <= len(recentes.json()) <= 10
    assert recentes.json()[0]["actor_name"] is not None


async def test_resumo_da_rede(cliente: httpx.AsyncClient, rede: dict[str, Any]) -> None:
    """009/R1.1 a R1.4."""
    resposta = await cliente.get(f"{PAINEL}/resumo", headers=rede["gestor"])

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert corpo["unidades"]["total"] == 3
    assert corpo["unidades"]["por_status"] == {"ativa": 3}
    assert corpo["qualidade"]["sem_cnes"] == 1
    assert corpo["qualidade"]["servicos_fora_cnes"] == 1
    assert corpo["alteracoes"]["ultimos_7_dias"] >= 6
    assert corpo["gerado_em"].endswith("-03:00")


async def test_escopo_do_tecnico_distrital_reduz_os_numeros(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, rede: dict[str, Any]
) -> None:
    """011/T22 (D3): com `dashboard:read` no distrito, o resumo e o inventário são do DS-I."""
    distrital = bearer(
        app, await logado(sessoes, ("TECNICO_DISTRITAL", ("distrito", str(rede["ds1"]))))
    )

    resumo = await cliente.get(f"{PAINEL}/resumo", headers=distrital)
    inventario = await cliente.get(f"{PAINEL}/inventario", headers=distrital)

    assert resumo.json()["unidades"]["total"] == 2
    assert {u["unit_id"] for u in inventario.json()["itens"]} == {rede["a"], rede["b"]}


async def test_filtro_de_area_inexistente_e_422(
    cliente: httpx.AsyncClient, rede: dict[str, Any]
) -> None:
    resposta = await cliente.get(f"{PAINEL}/resumo", params={"area": 999}, headers=rede["gestor"])

    assert resposta.status_code == 422


async def test_catalogo_lista_so_o_que_o_usuario_pode(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """011/R3.1, R3.2: a Diretoria (sem `auditoria:read`) não vê histórico, log e partições."""
    diretoria = bearer(app, await logado(sessoes, ("DIRETORIA", GLOBAL)))
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))

    da_diretoria = await cliente.get(f"{PAINEL}/consultas", headers=diretoria)
    do_gestor = await cliente.get(f"{PAINEL}/consultas", headers=gestor)

    nomes = {e["nome"] for e in da_diretoria.json()}
    assert "inventario" in nomes
    assert {"historico-da-unidade", "log-do-banco", "particoes-do-log"}.isdisjoint(nomes)
    entrada = next(e for e in do_gestor.json() if e["nome"] == "distritos-sem-cnes-acima-da-rede")
    assert entrada["tecnica_sql"] == "subconsulta escalar no HAVING"
    assert entrada["grafico_sugerido"]
    assert len(do_gestor.json()) == 13


async def test_auditor_sem_dashboard_read_recebe_403(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    auditor = bearer(app, await logado(sessoes, ("AUDITOR", GLOBAL)))

    resposta = await cliente.get(f"{PAINEL}/resumo", headers=auditor)

    assert resposta.status_code == 403


async def test_alteracoes_nao_contam_falhas_nem_acessos(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes, rede: dict[str, Any]
) -> None:
    """013/R8.8: uma tentativa que falhou (`operacao.falhou`) e uma negação de acesso numa
    unidade não mudam as contagens nem a lista de alterações do painel."""
    cabecalho = rede["gestor"]

    async def contagens() -> tuple[int, int, list[str]]:
        periodo = await cliente.get(f"{PAINEL}/consultas/alteracoes-por-periodo", headers=cabecalho)
        resumo = await cliente.get(f"{PAINEL}/resumo", headers=cabecalho)
        recentes = await cliente.get(f"{PAINEL}/consultas/alteracoes-recentes", headers=cabecalho)
        return (
            sum(d["last_30_days"] for d in periodo.json()),
            resumo.json()["alteracoes"]["ultimos_30_dias"],
            [r["action"] for r in recentes.json()],
        )

    antes = await contagens()
    falha = await cliente.patch(
        f"/api/v1/unidades/{rede['c']}", json={"bairro": "Derby"}, headers=cabecalho
    )  # 428 → operacao.falhou com a unidade na entidade
    alheia = await logado(sessoes, ("GESTOR_UNIDADE", ("unidade", rede["a"])))
    negado = await cliente.patch(
        f"/api/v1/unidades/{rede['c']}",
        json={"bairro": "Derby"},
        headers=bearer(app, alheia) | {"If-Match": '"1"'},
    )
    depois = await contagens()

    assert (falha.status_code, negado.status_code) == (428, 403)
    assert depois == antes
    assert "operacao.falhou" not in depois[2]
    assert "acesso.negado" not in depois[2]
