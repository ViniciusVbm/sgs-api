"""Serviços da unidade: incluir, consultar, alterar (PATCH parcial com nome, tipo, "no CNES" e
situação), desativar, reativar e remover, e o efeito do trigger trg_set_updated_at
(spec 012, T10: R8.1, R8.2; R7.4).

Cada teste cria a própria unidade e os próprios serviços pela API, no banco descartável do
compose do E2E (design § Dados nos E2E da emenda).
"""

import secrets
import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.e2e_front.apoio import api, nova_unidade, requisicao, token

Sessao = Callable[[str], Page]
CAMPOS_DO_PATCH = {"nome", "tipo_servico_id", "no_cnes", "status"}  # R8.2; sem equipamento_id


@pytest.fixture
def gestor(sessao_de: Sessao) -> Iterator[tuple[Page, str]]:
    pagina = sessao_de("GESTOR_DADOS")
    yield pagina, token(pagina)
    pagina.close()


def _abrir_servicos(pagina: Page, unidade_id: str) -> None:
    pagina.goto("/#/sem-acesso")
    with pagina.expect_response(f"**/api/v1/unidades/{unidade_id}/servicos"):
        pagina.goto(f"/#/unidade/{unidade_id}/servicos")
    expect(pagina.locator("[data-ref=total-servicos]")).to_be_visible()


def _tipos_ativos(pagina: Page, token_: str) -> list[dict[str, Any]]:
    return [t for t in api(pagina, token_, "/referencias/tipos-servico") if t["ativo"]]


def _servicos(pagina: Page, token_: str, unidade_id: str) -> list[dict[str, Any]]:
    servicos: list[dict[str, Any]] = api(pagina, token_, f"/unidades/{unidade_id}/servicos")
    return servicos


def _patch(pagina: Page) -> Any:
    return pagina.expect_request(lambda r: r.method == "PATCH" and "/servicos/" in r.url)


def test_incluir_alterar_desativar_reativar_e_remover(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)
    tipo_a, tipo_b = _tipos_ativos(pagina, token_)[:2]
    _abrir_servicos(pagina, unidade["id"])
    expect(pagina.locator("[data-servico]")).to_have_count(0)

    # Incluir
    nome = f"Sala de vacina {secrets.token_hex(2)}"
    pagina.click("#incluir-servico")
    pagina.fill("#fld-nome", nome)
    pagina.select_option("#fld-tipo_servico_id", str(tipo_a["id"]))
    pagina.select_option("#fld-no_cnes", "true")
    with pagina.expect_request(lambda r: r.method == "POST") as criacao:
        pagina.click("#fs button[type=submit]")
    assert criacao.value.post_data_json == {
        "nome": nome,
        "tipo_servico_id": tipo_a["id"],
        "no_cnes": True,
        "status": "ativo",
    }
    expect(pagina.locator("[data-servico]")).to_have_count(1)
    (servico,) = _servicos(pagina, token_, unidade["id"])
    linha = pagina.locator(f"tr[data-servico='{servico['id']}']")
    expect(linha.locator("[data-ref=servico-nome]")).to_have_text(nome)
    expect(linha.locator("[data-ref=servico-tipo]")).to_have_text(tipo_a["nome"])
    expect(linha.locator("[data-ref=servico-cnes]")).to_have_text("Sim")

    # Alterar os quatro campos do R8.2: o PATCH leva só eles
    novo_nome = f"{nome} (renomeado)"
    linha.locator("[data-editar-servico]").click()
    expect(pagina.locator("#fld-equipamento_id")).to_have_count(0)  # vínculo não editável (DF1)
    pagina.fill("#fld-nome", novo_nome)
    pagina.select_option("#fld-tipo_servico_id", str(tipo_b["id"]))
    pagina.select_option("#fld-no_cnes", "false")
    pagina.select_option("#fld-status", "inativo")
    with _patch(pagina) as alteracao:
        pagina.click("#fs button[type=submit]")
    corpo = alteracao.value.post_data_json
    assert set(corpo) == CAMPOS_DO_PATCH
    assert corpo == {
        "nome": novo_nome,
        "tipo_servico_id": tipo_b["id"],
        "no_cnes": False,
        "status": "inativo",
    }
    expect(linha.locator("[data-ref=servico-status]")).to_have_text("Inativo")
    (gravado,) = _servicos(pagina, token_, unidade["id"])
    assert {k: gravado[k] for k in CAMPOS_DO_PATCH} == corpo

    # Só um campo alterado: o PATCH leva só ele
    linha.locator("[data-editar-servico]").click()
    pagina.fill("#fld-nome", nome)
    with _patch(pagina) as parcial:
        pagina.click("#fs button[type=submit]")
    assert parcial.value.post_data_json == {"nome": nome}

    # Reativar e desativar pelo atalho (PATCH de status)
    for status, rotulo in (("ativo", "Ativo"), ("inativo", "Inativo")):
        linha.locator("[data-situacao-servico]").click()
        with _patch(pagina) as pedido:
            pagina.click("#cs-confirmar")
        assert pedido.value.post_data_json == {"status": status}
        expect(linha.locator("[data-ref=servico-status]")).to_have_text(rotulo)

    # Remover (DELETE do R8.1)
    linha.locator("[data-remover-servico]").click()
    with pagina.expect_response(lambda r: r.request.method == "DELETE") as remocao:
        pagina.click("#cs-confirmar")
    assert remocao.value.status == 204
    expect(pagina.locator("[data-servico]")).to_have_count(0)
    assert _servicos(pagina, token_, unidade["id"]) == []

    acoes = [
        e["acao"] for e in api(pagina, token_, f"/unidades/{unidade['id']}/historico")["itens"]
    ]
    assert "unidade.servico_adicionado" in acoes
    assert acoes.count("unidade.servico_alterado") == 4
    assert "unidade.servico_removido" in acoes


def test_patch_muda_o_updated_at_pelo_trigger(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)
    tipo = _tipos_ativos(pagina, token_)[0]
    criado = api(
        pagina,
        token_,
        f"/unidades/{unidade['id']}/servicos",
        "POST",
        {"nome": "Farmácia de teste", "tipo_servico_id": tipo["id"]},
    )
    time.sleep(1.2)  # para a diferença também aparecer nos segundos exibidos
    _abrir_servicos(pagina, unidade["id"])
    linha = pagina.locator(f"tr[data-servico='{criado['id']}']")
    expect(linha.locator("[data-ref=servico-atualizado]")).to_have_attribute(
        "data-iso", criado["atualizado_em"]
    )
    antes_na_tela = linha.locator("[data-ref=servico-atualizado]").inner_text()
    linha.locator("[data-editar-servico]").click()
    pagina.fill("#fld-nome", "Farmácia de teste (alterada)")
    with pagina.expect_response(lambda r: r.request.method == "PATCH") as resposta:
        pagina.click("#fs button[type=submit]")
    depois = resposta.value.json()["atualizado_em"]
    assert depois > criado["atualizado_em"]  # gravado pelo banco: o PATCH não envia a data
    assert "atualizado_em" not in (resposta.value.request.post_data_json or {})
    efeito = pagina.locator("[data-ref=efeito-updated-at]")
    expect(efeito).to_have_attribute("data-antes", criado["atualizado_em"])
    expect(efeito).to_have_attribute("data-depois", depois)
    expect(efeito).to_contain_text("trg_set_updated_at")
    expect(linha.locator("[data-ref=servico-atualizado]")).to_have_attribute("data-iso", depois)
    assert linha.locator("[data-ref=servico-atualizado]").inner_text() != antes_na_tela
    assert _servicos(pagina, token_, unidade["id"])[0]["atualizado_em"] == depois


def test_tipo_inativo_volta_como_erro_da_api_no_campo(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)
    codigo = f"E2E_SRV_{secrets.token_hex(3).upper()}"
    tipo = api(
        pagina, token_, "/referencias/tipos-servico", "POST", {"codigo": codigo, "nome": codigo}
    )
    _abrir_servicos(pagina, unidade["id"])
    pagina.click("#incluir-servico")
    pagina.fill("#fld-nome", "Serviço com tipo que vai ser desativado")
    pagina.select_option("#fld-tipo_servico_id", str(tipo["id"]))
    api(pagina, token_, f"/referencias/tipos-servico/{tipo['id']}", "PATCH", {"ativo": False})
    with pagina.expect_response(lambda r: r.request.method == "POST") as resposta:
        pagina.click("#fs button[type=submit]")
    assert resposta.value.status == 422
    erro = next(e for e in resposta.value.json()["errors"] if e["campo"] == "tipo_servico_id")
    caixa = pagina.locator("[data-campo=tipo_servico_id]")
    expect(caixa).to_have_class("fld bad")
    expect(caixa.locator(".fld-err")).to_have_text(erro["mensagem"])
    assert _servicos(pagina, token_, unidade["id"]) == []


def _unidade_do_escopo(pagina: Page, token_: str, papel: str) -> str:
    me = api(pagina, token_, "/me")
    if papel == "GESTOR_UNIDADE":
        return str(
            next(e["id"] for e in me["permissoes"]["servico:write"] if e["tipo"] == "unidade")
        )
    if papel == "TECNICO_DISTRITAL":
        distrito = next(
            e["id"] for e in me["permissoes"]["servico:write"] if e["tipo"] == "distrito"
        )
        return str(
            api(pagina, token_, f"/unidades?distrito={distrito}&tamanho=1")["itens"][0]["id"]
        )
    if papel == "COORD_TECNICO":
        area = next(e["id"] for e in me["permissoes"]["servico:write"] if e["tipo"] == "area")
        inventario = api(pagina, token_, f"/dashboard/inventario?area={area}&tamanho=1")
        return str(inventario["itens"][0]["unit_id"])
    return str(api(pagina, token_, "/unidades?tamanho=1")["itens"][0]["id"])


# R8.1 remete ao R7.4: até a DF2/DF14, só o escopo global vê os controles. A restrição é da
# interface, não da API: quem tem servico:write no próprio escopo (Técnico Distrital, Gestor de
# Unidade, Coordenador Técnico) continua aceito pela API; quem não tem a permissão (Diretoria)
# recebe 403.
@pytest.mark.parametrize(
    ("papel", "status_da_api"),
    [
        ("TECNICO_DISTRITAL", 201),
        ("GESTOR_UNIDADE", 201),
        ("COORD_TECNICO", 201),
        ("DIRETORIA", 403),
    ],
)
def test_so_o_escopo_global_ve_os_controles(
    sessao_de: Sessao, papel: str, status_da_api: int
) -> None:
    pagina = sessao_de(papel)
    token_ = token(pagina)
    unidade_id = _unidade_do_escopo(pagina, token_, papel)
    _abrir_servicos(pagina, unidade_id)
    expect(pagina.locator("#incluir-servico")).to_have_count(0)
    expect(
        pagina.locator("[data-editar-servico], [data-situacao-servico], [data-remover-servico]")
    ).to_have_count(0)
    tipo = _tipos_ativos(pagina, token_)[0]
    resposta = requisicao(
        pagina,
        token_,
        "POST",
        f"/unidades/{unidade_id}/servicos",
        {"nome": "Serviço da conferência da matriz", "tipo_servico_id": tipo["id"]},
    )
    assert resposta.status == status_da_api
    if resposta.status == 201:  # devolve o banco ao estado anterior
        criado = resposta.json()
        apagado = requisicao(
            pagina, token_, "DELETE", f"/unidades/{unidade_id}/servicos/{criado['id']}"
        )
        assert apagado.status == 204


@pytest.mark.parametrize("largura", [1280, 390])
def test_sem_rolagem_horizontal(gestor: tuple[Page, str], largura: int) -> None:
    pagina, token_ = gestor
    pagina.set_viewport_size({"width": largura, "height": 900})
    unidade = nova_unidade(pagina, token_)
    tipo = _tipos_ativos(pagina, token_)[0]
    api(
        pagina,
        token_,
        f"/unidades/{unidade['id']}/servicos",
        "POST",
        {"nome": "Serviço para a largura", "tipo_servico_id": tipo["id"]},
    )
    _abrir_servicos(pagina, unidade["id"])
    expect(pagina.locator("[data-servico]")).to_have_count(1)
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    pagina.click("#incluir-servico")
    expect(pagina.locator("#fs")).to_be_visible()
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
