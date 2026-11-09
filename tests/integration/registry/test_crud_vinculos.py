"""Equipamentos, serviços e referências (006/T7 a T9; 011/T18).

Com unidade: escopo da unidade, auditoria no nível dela (R5.3). Soltos: só escopo global.
Referências: só o Gestor de Dados escreve; a correção do código do tipo de equipamento chega aos
equipamentos pela cascata e é auditada com a quantidade afetada.
"""

from typing import Any

import httpx
from fastapi import FastAPI

from tests.integration.acesso import GLOBAL, Sessoes, bearer, eventos, id_pelo_codigo, logado

UNIDADES = "/api/v1/unidades"


async def _unidade(
    cliente: httpx.AsyncClient, sessoes: Sessoes, cabecalho: dict[str, str], nome: str
) -> str:
    corpo: dict[str, Any] = {
        "nome": nome,
        "tipo_unidade_id": await id_pelo_codigo(sessoes, "tipo_unidade", "CAPS_II"),
        "distrito_id": await id_pelo_codigo(sessoes, "distrito", "DS-I"),
        "cep": "50010100",
        "endereco": "Rua do Sol, 150",
        "status": "ativa",
    }
    resposta = await cliente.post(UNIDADES, json=corpo, headers=cabecalho)
    assert resposta.status_code == 201, resposta.text
    return str(resposta.json()["id"])


async def test_equipamento_da_unidade_crud_completo_com_auditoria(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R5.1, R5.3; 011/R9.1: criar, listar, alterar, remover; o serviço ligado fica."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _unidade(cliente, sessoes, gestor, "CAPS Equipado")
    base = f"{UNIDADES}/{unidade}/equipamentos"

    criado = await cliente.post(
        base,
        json={"nome": "Maternidade anexa", "tipo_codigo": "MATERNIDADE", "quantidade": 2},
        headers=gestor,
    )
    equipamento = criado.json()["id"]
    servico = await cliente.post(
        f"{UNIDADES}/{unidade}/servicos",
        json={
            "nome": "Farmácia",
            "tipo_servico_id": await _tipo_de_servico(cliente, gestor, "FARMACIA"),
            "equipamento_id": equipamento,
        },
        headers=gestor,
    )
    alterado = await cliente.patch(f"{base}/{equipamento}", json={"quantidade": 3}, headers=gestor)
    nulo = await cliente.patch(f"{base}/{equipamento}", json={"quantidade": None}, headers=gestor)
    removido = await cliente.delete(f"{base}/{equipamento}", headers=gestor)
    lista = await cliente.get(base, headers=gestor)
    servicos = await cliente.get(f"{UNIDADES}/{unidade}/servicos", headers=gestor)

    assert criado.status_code == 201
    assert servico.status_code == 201, servico.text
    assert alterado.status_code == 200
    assert alterado.json()["quantidade"] == 3
    assert nulo.status_code == 422  # a 003 dava 500 aqui (P15 do doc 06)
    assert removido.status_code == 204
    assert lista.json() == []
    assert servicos.json()[0]["equipamento_id"] is None
    acoes = [
        e["metadata"].get("equipamento_id")
        for e in await eventos(sessoes, "unidade.equipamento_removido")
    ]
    assert acoes == [equipamento]
    [remocao] = await eventos(sessoes, "unidade.equipamento_removido")
    assert remocao["entity_type"] == "unidade"
    assert remocao["entity_id"] == unidade
    assert remocao["metadata"]["servicos_desvinculados"] == 1


async def test_equipamento_de_outra_unidade_e_404(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    uma = await _unidade(cliente, sessoes, gestor, "CAPS Um")
    outra = await _unidade(cliente, sessoes, gestor, "CAPS Outra")
    criado = await cliente.post(
        f"{UNIDADES}/{uma}/equipamentos",
        json={"nome": "Policlínica", "tipo_codigo": "POLICLINICA"},
        headers=gestor,
    )

    resposta = await cliente.patch(
        f"{UNIDADES}/{outra}/equipamentos/{criado.json()['id']}",
        json={"quantidade": 2},
        headers=gestor,
    )

    assert resposta.status_code == 404


async def test_escopo_da_unidade_vale_para_equipamentos(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R5.1: Gestor de Unidade escreve só na própria."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    minha = await _unidade(cliente, sessoes, gestor, "CAPS Minha")
    alheia = await _unidade(cliente, sessoes, gestor, "CAPS Alheia")
    da_unidade = bearer(app, await logado(sessoes, ("GESTOR_UNIDADE", ("unidade", minha))))
    corpo = {"nome": "Policlínica", "tipo_codigo": "POLICLINICA"}

    ok = await cliente.post(f"{UNIDADES}/{minha}/equipamentos", json=corpo, headers=da_unidade)
    negado = await cliente.post(f"{UNIDADES}/{alheia}/equipamentos", json=corpo, headers=da_unidade)

    assert ok.status_code == 201
    assert negado.status_code == 403


async def test_equipamento_solto_so_com_escopo_global(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R5.2: UTI móvel sem unidade só pelo Gestor de Dados."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    area = await id_pelo_codigo(sessoes, "area", "SAUDE_MENTAL")
    coordenador = bearer(app, await logado(sessoes, ("COORD_TECNICO", ("area", str(area)))))
    corpo = {"nome": "UTI móvel 1", "tipo_codigo": "UTI_MOVEL"}

    negado = await cliente.post("/api/v1/equipamentos", json=corpo, headers=coordenador)
    criado = await cliente.post("/api/v1/equipamentos", json=corpo, headers=gestor)
    lista = await cliente.get("/api/v1/equipamentos", headers=gestor)

    assert negado.status_code == 403
    assert criado.status_code == 201
    assert criado.json()["unidade_id"] is None
    assert [e["nome"] for e in lista.json()] == ["UTI móvel 1"]
    assert len(await eventos(sessoes, "equipamento.adicionado")) == 1


async def test_tipo_de_equipamento_inexistente_e_422(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _unidade(cliente, sessoes, gestor, "CAPS Tipo")

    resposta = await cliente.post(
        f"{UNIDADES}/{unidade}/equipamentos",
        json={"nome": "X", "tipo_codigo": "NAO_EXISTE"},
        headers=gestor,
    )

    assert resposta.status_code == 422


async def test_servico_com_equipamento_de_outra_unidade_e_422(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    uma = await _unidade(cliente, sessoes, gestor, "CAPS Um")
    outra = await _unidade(cliente, sessoes, gestor, "CAPS Outra")
    equipamento = await cliente.post(
        f"{UNIDADES}/{uma}/equipamentos",
        json={"nome": "Poli", "tipo_codigo": "POLICLINICA"},
        headers=gestor,
    )

    resposta = await cliente.post(
        f"{UNIDADES}/{outra}/servicos",
        json={
            "nome": "Farmácia",
            "tipo_servico_id": await _tipo_de_servico(cliente, gestor, "FARMACIA"),
            "equipamento_id": equipamento.json()["id"],
        },
        headers=gestor,
    )

    assert resposta.status_code == 422


async def test_servico_solto_e_alteracao_e_remocao(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R6.2, R6.3."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    tipo = await _tipo_de_servico(cliente, gestor, "SALA_VACINA")

    criado = await cliente.post(
        "/api/v1/servicos",
        json={"nome": "Vacina do Shopping", "tipo_servico_id": tipo},
        headers=gestor,
    )
    alterado = await cliente.patch(
        f"/api/v1/servicos/{criado.json()['id']}", json={"no_cnes": True}, headers=gestor
    )
    removido = await cliente.delete(f"/api/v1/servicos/{criado.json()['id']}", headers=gestor)

    assert criado.status_code == 201
    assert criado.json()["unidade_id"] is None
    assert alterado.json()["no_cnes"] is True
    assert removido.status_code == 204


async def test_referencias_listar_criar_e_corrigir_codigo_com_cascata(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R7.1 a R7.3; 011/T18, R9.2."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _unidade(cliente, sessoes, gestor, "CAPS Ref")
    novo = await cliente.post(
        "/api/v1/referencias/tipos-equipamento",
        json={"codigo": "AMBULATORIO", "nome": "Ambulatório"},
        headers=gestor,
    )
    repetido = await cliente.post(
        "/api/v1/referencias/tipos-equipamento",
        json={"codigo": "AMBULATORIO", "nome": "Outro"},
        headers=gestor,
    )
    for numero in range(2):
        await cliente.post(
            f"{UNIDADES}/{unidade}/equipamentos",
            json={"nome": f"Ambulatório {numero}", "tipo_codigo": "AMBULATORIO"},
            headers=gestor,
        )

    corrigido = await cliente.patch(
        f"/api/v1/referencias/tipos-equipamento/{novo.json()['id']}",
        json={"codigo": "AMBULATORIO_GERAL"},
        headers=gestor,
    )
    equipamentos = await cliente.get(f"{UNIDADES}/{unidade}/equipamentos", headers=gestor)
    lista = await cliente.get("/api/v1/referencias/distritos", headers=gestor)

    assert novo.status_code == 201
    assert repetido.status_code == 409
    assert corrigido.status_code == 200, corrigido.text
    assert {e["tipo_codigo"] for e in equipamentos.json()} == {"AMBULATORIO_GERAL"}
    [evento] = await eventos(sessoes, "referencia.atualizada")
    assert evento["metadata"] == {"equipamentos_afetados": 2}
    assert len(lista.json()) == 8


async def test_so_o_gestor_de_dados_escreve_referencias(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R7.2."""
    area = await id_pelo_codigo(sessoes, "area", "SAUDE_MENTAL")
    coordenador = bearer(app, await logado(sessoes, ("COORD_TECNICO", ("area", str(area)))))

    leitura = await cliente.get("/api/v1/referencias/tipos-unidade", headers=coordenador)
    escrita = await cliente.post(
        "/api/v1/referencias/tipos-servico", json={"codigo": "X", "nome": "X"}, headers=coordenador
    )

    assert leitura.status_code == 200
    assert escrita.status_code == 403


async def _tipo_de_servico(
    cliente: httpx.AsyncClient, cabecalho: dict[str, str], codigo: str
) -> int:
    lista = await cliente.get("/api/v1/referencias/tipos-servico", headers=cabecalho)
    return int(next(item["id"] for item in lista.json() if item["codigo"] == codigo))
