"""CRUD da unidade: listar, detalhar, atualizar e desativar (006/T4 a T6; 011/T16, T17, T21).

Os dados entram pela própria API (POST), como faria o front, e conferimos resposta, banco e
trilha de auditoria.
"""

from typing import Any
from uuid import UUID

import httpx
from fastapi import FastAPI
from sqlalchemy import text

from tests.integration.acesso import GLOBAL, Sessoes, bearer, eventos, id_pelo_codigo, logado

ROTA = "/api/v1/unidades"


async def _criar(
    app: FastAPI,
    cliente: httpx.AsyncClient,
    sessoes: Sessoes,
    cabecalho: dict[str, str],
    **campos: Any,
) -> dict[str, Any]:
    corpo: dict[str, Any] = {
        "nome": "CAPS Espaço Azul",
        "tipo_unidade_id": await id_pelo_codigo(sessoes, "tipo_unidade", "CAPS_II"),
        "distrito_id": await id_pelo_codigo(sessoes, "distrito", "DS-I"),
        "cep": "50010100",
        "endereco": "Rua do Sol, 150",
        "status": "ativa",
    } | campos
    resposta = await cliente.post(ROTA, json=corpo, headers=cabecalho)
    assert resposta.status_code == 201, resposta.text
    return dict(resposta.json())


async def test_lista_paginada_com_busca_sem_acento_e_filtros(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R2.1 a R2.3: paginação com total, `q` sem acento e caixa, filtros combinados."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    ds2 = await id_pelo_codigo(sessoes, "distrito", "DS-II")
    await _criar(app, cliente, sessoes, gestor, nome="CAPS José Carlos Souto", cnes="2345678")
    await _criar(app, cliente, sessoes, gestor, nome="CAPS Galdino Loreto", distrito_id=ds2)
    await _criar(app, cliente, sessoes, gestor, nome="CAPS Espaço Livre", status="em_implantacao")

    busca = await cliente.get(ROTA, params={"q": "JOSE carlos"}, headers=gestor)
    pelo_cnes = await cliente.get(ROTA, params={"q": "23456"}, headers=gestor)
    filtrada = await cliente.get(ROTA, params={"distrito": ds2, "status": "ativa"}, headers=gestor)
    pagina = await cliente.get(ROTA, params={"tamanho": 2, "pagina": 2}, headers=gestor)

    assert [u["nome"] for u in busca.json()["itens"]] == ["CAPS José Carlos Souto"]
    assert [u["cnes"] for u in pelo_cnes.json()["itens"]] == ["2345678"]
    assert [u["nome"] for u in filtrada.json()["itens"]] == ["CAPS Galdino Loreto"]
    assert pagina.json()["total"] == 3
    assert len(pagina.json()["itens"]) == 1


async def test_busca_com_curinga_do_like_e_literal(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """`%` e `_` digitados pelo usuário não viram curinga."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    await _criar(app, cliente, sessoes, gestor, nome="CAPS Azul")

    resposta = await cliente.get(ROTA, params={"q": "%"}, headers=gestor)

    assert resposta.json()["total"] == 0


async def test_detalhe_traz_vinculos_e_etag(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R2.5: a unidade com equipamentos e serviços; o ETag é a versão."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _criar(app, cliente, sessoes, gestor)
    await cliente.post(
        f"{ROTA}/{unidade['id']}/equipamentos",
        json={"nome": "Policlínica anexa", "tipo_codigo": "POLICLINICA"},
        headers=gestor,
    )

    resposta = await cliente.get(f"{ROTA}/{unidade['id']}", headers=gestor)

    assert resposta.status_code == 200
    assert resposta.headers["ETag"] == '"1"'
    assert [e["nome"] for e in resposta.json()["equipamentos"]] == ["Policlínica anexa"]
    assert resposta.json()["servicos"] == []


async def test_detalhe_de_unidade_inexistente_e_404(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))

    resposta = await cliente.get(f"{ROTA}/0192f000-0000-7000-8000-000000000000", headers=gestor)

    assert resposta.status_code == 404


async def test_patch_aplica_so_os_campos_enviados_e_audita_o_diff(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R3.1, R3.5; 011/T17: a versão sobe pelo trigger; a trilha guarda de/para."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _criar(app, cliente, sessoes, gestor, telefone="(81) 3355-0000")

    resposta = await cliente.patch(
        f"{ROTA}/{unidade['id']}",
        json={"telefone": "(81) 3355-1111", "bairro": "Boa Vista"},
        headers=gestor | {"If-Match": '"1"'},
    )

    assert resposta.status_code == 200, resposta.text
    assert resposta.headers["ETag"] == '"2"'
    assert resposta.json()["telefone"] == "(81) 3355-1111"
    assert resposta.json()["endereco"] == "Rua do Sol, 150"
    [evento] = await eventos(sessoes, "unidade.atualizada")
    assert sorted(evento["changes"], key=lambda m: m["campo"]) == [
        {"campo": "neighborhood", "de": None, "para": "Boa Vista"},
        {"campo": "phone", "de": "(81) 3355-0000", "para": "(81) 3355-1111"},
    ]


async def test_patch_sem_if_match_e_428_e_com_versao_antiga_e_412(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R3.2."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _criar(app, cliente, sessoes, gestor)
    url = f"{ROTA}/{unidade['id']}"

    sem = await cliente.patch(url, json={"bairro": "Derby"}, headers=gestor)
    await cliente.patch(url, json={"bairro": "Derby"}, headers=gestor | {"If-Match": '"1"'})
    antiga = await cliente.patch(
        url, json={"bairro": "Graças"}, headers=gestor | {"If-Match": '"1"'}
    )

    assert sem.status_code == 428
    assert antiga.status_code == 412
    assert antiga.json()["versao_atual"] == "2"


async def test_alteracao_fora_da_api_invalida_o_etag(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """011/T17, R8.3: UPDATE direto no banco sobe a versão; o ETag antigo dá 412."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _criar(app, cliente, sessoes, gestor)
    async with sessoes() as sessao, sessao.begin():
        await sessao.execute(
            text("UPDATE health_units SET phone = '(81) 9999-0000' WHERE id = :id"),
            {"id": UUID(unidade["id"])},
        )

    resposta = await cliente.patch(
        f"{ROTA}/{unidade['id']}", json={"bairro": "Derby"}, headers=gestor | {"If-Match": '"1"'}
    )

    assert resposta.status_code == 412


async def test_patch_sem_mudanca_responde_200_sem_auditoria(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R3.6."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _criar(app, cliente, sessoes, gestor)

    resposta = await cliente.patch(
        f"{ROTA}/{unidade['id']}",
        json={"nome": "CAPS Espaço Azul"},
        headers=gestor | {"If-Match": '"1"'},
    )

    assert resposta.status_code == 200
    assert resposta.headers["ETag"] == '"1"'
    assert await eventos(sessoes, "unidade.atualizada") == []


async def test_gestor_de_unidade_nao_altera_campos_estruturais(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R3.3, R3.4: com escopo de unidade, distrito, tipo e CNES dão 403 e nada muda."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _criar(app, cliente, sessoes, gestor)
    da_unidade = bearer(app, await logado(sessoes, ("GESTOR_UNIDADE", ("unidade", unidade["id"]))))

    estrutural = await cliente.patch(
        f"{ROTA}/{unidade['id']}",
        json={"cnes": "7654321"},
        headers=da_unidade | {"If-Match": '"1"'},
    )
    comum = await cliente.patch(
        f"{ROTA}/{unidade['id']}",
        json={"bairro": "Derby"},
        headers=da_unidade | {"If-Match": '"1"'},
    )

    assert estrutural.status_code == 403
    assert estrutural.json()["campos_estruturais"] == "cnes"
    assert comum.status_code == 200


async def test_patch_que_repete_o_nome_de_outra_e_409(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R1.4 também na atualização."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    primeira = await _criar(app, cliente, sessoes, gestor, nome="CAPS Um")
    segunda = await _criar(app, cliente, sessoes, gestor, nome="CAPS Dois")

    resposta = await cliente.patch(
        f"{ROTA}/{segunda['id']}", json={"nome": "caps  UM"}, headers=gestor | {"If-Match": '"1"'}
    )

    assert resposta.status_code == 409
    assert resposta.json()["unidade_existente_id"] == primeira["id"]


async def test_patch_nao_desativa_nem_esvazia_obrigatorio(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _criar(app, cliente, sessoes, gestor)

    resposta = await cliente.patch(
        f"{ROTA}/{unidade['id']}",
        json={"status": "inativa", "endereco": None},
        headers=gestor | {"If-Match": '"1"'},
    )

    assert resposta.status_code == 422
    campos = {erro["campo"] for erro in resposta.json()["errors"]}
    assert campos == {"status", "endereco"}


async def test_desativar_pela_procedure_audita_uma_vez(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R4, 011/T16: 200 com `unidade.desativada` e motivo; de novo, 200 sem auditoria."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _criar(app, cliente, sessoes, gestor)
    url = f"{ROTA}/{unidade['id']}/desativar"

    primeira = await cliente.post(url, json={"motivo": "Unidade fechada"}, headers=gestor)
    segunda = await cliente.post(url, json={"motivo": "Repetido"}, headers=gestor)

    assert primeira.status_code == segunda.status_code == 200
    assert primeira.json()["status"] == "inativa"
    [evento] = await eventos(sessoes, "unidade.desativada")
    assert evento["metadata"] == {"motivo": "Unidade fechada"}
    async with sessoes() as sessao:
        assert (
            await sessao.scalar(
                text("SELECT count(*) FROM health_units WHERE id = :id"),
                {"id": UUID(unidade["id"])},
            )
            == 1
        )


async def test_desativar_exige_permissao_e_unidade_existente(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """006/R4.1: só `unidade:deactivate` (Gestor de Dados); inexistente, 404."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _criar(app, cliente, sessoes, gestor)
    distrital = bearer(
        app,
        await logado(
            sessoes,
            (
                "TECNICO_DISTRITAL",
                ("distrito", str(await id_pelo_codigo(sessoes, "distrito", "DS-I"))),
            ),
        ),
    )

    negado = await cliente.post(
        f"{ROTA}/{unidade['id']}/desativar", json={"motivo": "Teste"}, headers=distrital
    )
    inexistente = await cliente.post(
        f"{ROTA}/0192f000-0000-7000-8000-000000000000/desativar",
        json={"motivo": "Teste"},
        headers=gestor,
    )

    assert negado.status_code == 403
    assert inexistente.status_code == 404


async def test_trilha_mascara_o_nome_do_gestor_e_grava_o_papel(
    app: FastAPI, cliente: httpx.AsyncClient, sessoes: Sessoes
) -> None:
    """011/T21 (D2, LGPD): `manager_name` vai como `***`; `actor_roles` traz o papel."""
    gestor = bearer(app, await logado(sessoes, ("GESTOR_DADOS", GLOBAL)))
    unidade = await _criar(app, cliente, sessoes, gestor, nome_gestor="Ana Souza")
    await cliente.patch(
        f"{ROTA}/{unidade['id']}",
        json={"nome_gestor": "Bruno Lima"},
        headers=gestor | {"If-Match": '"1"'},
    )

    async with sessoes() as sessao:
        linhas = (
            await sessao.execute(
                text(
                    "SELECT action, actor_roles, changes FROM audit_log"
                    " WHERE entity_id = :id ORDER BY id"
                ),
                {"id": unidade["id"]},
            )
        ).all()
    criada, atualizada = linhas

    assert criada.actor_roles == ["GESTOR_DADOS"]
    gestor_criado = next(m for m in criada.changes if m["campo"] == "manager_name")
    assert gestor_criado == {"campo": "manager_name", "de": None, "para": "***"}
    assert atualizada.changes == [{"campo": "manager_name", "de": "***", "para": "***"}]
    assert "Ana Souza" not in str(linhas)
