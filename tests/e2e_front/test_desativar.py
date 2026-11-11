"""Desativação da unidade pela procedure sp_deactivate_unit, a partir da ficha (spec 012, T25:
R7.7; 006/R4, 011/R6.2 a R6.4).

Cada teste desativa uma unidade criada por ele mesmo, pela API, no banco descartável do compose
do E2E (design § Dados nos E2E da emenda). Os efeitos conferidos: situação, versão (trigger de
versão), "Atualizado em", histórico com o motivo e a linha UPDATE no log do banco (trigger
trg_registry_change_log). A unidade nunca é apagada.
"""

import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from playwright.sync_api import Page, expect

from tests.e2e_front.apoio import api, nova_unidade, requisicao, token

Sessao = Callable[[str], Page]


@pytest.fixture
def gestor(sessao_de: Sessao) -> Iterator[tuple[Page, str]]:
    pagina = sessao_de("GESTOR_DADOS")
    yield pagina, token(pagina)
    pagina.close()


def _abrir(pagina: Page, unidade_id: str, aba: str = "") -> None:
    caminho = f"/api/v1/unidades/{unidade_id}"
    with pagina.expect_response(lambda r: r.url.endswith(caminho)):
        pagina.goto("/#/sem-acesso")
        pagina.goto(f"/#/unidade/{unidade_id}{'/' + aba if aba else ''}")
    expect(pagina.locator("[data-ref=nome-unidade]")).to_be_visible()


def test_desativar_pela_ficha_mostra_os_efeitos_da_procedure(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)
    posts: list[str] = []
    pagina.on("request", lambda r: posts.append(r.url) if r.method == "POST" else None)
    _abrir(pagina, unidade["id"])
    expect(pagina.locator("[data-ref=versao]")).to_have_text(str(unidade["versao"]))
    pagina.click("[data-ref=desativar]")
    expect(pagina.locator("[data-ref=nao-e-exclusao]")).to_contain_text("Desativar não é excluir")
    expect(pagina.locator("[data-ref=nao-e-exclusao]")).to_contain_text("sp_deactivate_unit")

    # Motivo curto: erro no campo e nada enviado
    pagina.fill("#fld-motivo", "ab")
    pagina.click("#fd button[type=submit]")
    expect(pagina.locator("[data-campo=motivo] .fld-err")).to_contain_text("pelo menos 3")
    assert posts == []

    motivo = "Unidade transferida para outro endereço"
    pagina.fill("#fld-motivo", motivo)
    with pagina.expect_response("**/desativar") as resposta:
        pagina.click("#fd button[type=submit]")
    assert resposta.value.status == 200
    assert resposta.value.request.post_data_json == {"motivo": motivo}
    devolvida = resposta.value.json()
    assert devolvida["status"] == "inativa"
    assert devolvida["versao"] == unidade["versao"] + 1  # o UPDATE da procedure dispara o trigger
    assert devolvida["atualizado_em"] > unidade["atualizado_em"]

    # A ficha recarregada: situação, versão, ETag e data novas; sem o botão
    expect(pagina.locator("[data-ref=status]")).to_have_text("Inativa")
    expect(pagina.locator("[data-ref=versao]")).to_have_text(str(devolvida["versao"]))
    expect(pagina.locator("[data-ref=ficha]")).to_have_attribute(
        "data-etag", f'"{devolvida["versao"]}"'
    )
    expect(pagina.locator("[data-ref=atualizado-em]")).to_have_attribute(
        "data-iso", devolvida["atualizado_em"]
    )
    expect(pagina.locator("[data-ref=desativar]")).to_have_count(0)
    aviso = pagina.locator("[data-ref=aviso-desativacao]")
    expect(aviso).to_have_attribute("data-versao-antes", str(unidade["versao"]))
    expect(aviso).to_have_attribute("data-versao-depois", str(devolvida["versao"]))
    expect(aviso).to_contain_text("não foi apagada")

    # Continua no cadastro (exclusão lógica)
    gravada = api(pagina, token_, f"/unidades/{unidade['id']}")
    assert (gravada["status"], gravada["versao"]) == ("inativa", devolvida["versao"])

    # Histórico da ficha: o evento com o motivo
    with pagina.expect_response("**/historico?*"):
        pagina.click("[data-ref=ver-historico]")
    primeiro = pagina.locator("[data-ref=historico] > li").first
    expect(primeiro.locator(".what")).to_have_text("Unidade desativada")
    expect(primeiro.locator("[data-ref=motivo]")).to_have_text(f"Motivo: {motivo}")
    expect(primeiro.locator(".changes")).to_contain_text("ativa")

    # Log do banco: a linha UPDATE gravada pelo trigger durante a procedure
    log = api(pagina, token_, "/auditoria/banco?tabela=health_units&tamanho=100")["itens"]
    linha = next(r for r in log if r["linha_id"] == unidade["id"] and r["operacao"] == "UPDATE")
    assert linha["colunas"]["status"] == {"de": "ativa", "para": "inativa"}
    assert linha["pela_api"] is True
    pagina.goto("/#/historico?aba=banco&tabela=health_units")
    expect(pagina.locator(f"tr[data-linha='{unidade['id']}']").first).to_be_visible()


def test_unidade_desativada_por_outra_sessao_com_o_modal_aberto(gestor: tuple[Page, str]) -> None:
    pagina, token_ = gestor
    unidade = nova_unidade(pagina, token_)
    _abrir(pagina, unidade["id"])
    pagina.click("[data-ref=desativar]")
    pagina.fill("#fld-motivo", "Desativação concorrente")
    api(pagina, token_, f"/unidades/{unidade['id']}/desativar", "POST", {"motivo": "Outra sessão"})
    desativacoes: list[str] = []
    pagina.on(
        "request", lambda r: desativacoes.append(r.url) if r.url.endswith("/desativar") else None
    )
    pagina.click("#fd button[type=submit]")
    aviso = pagina.locator("[data-ref=aviso-desativacao]")
    expect(aviso).to_have_attribute("data-tipo", "ja-inativa")
    expect(pagina.locator("[data-ref=status]")).to_have_text("Inativa")
    assert desativacoes == []  # a tela releu a unidade e não enviou a segunda desativação
    eventos = api(pagina, token_, f"/unidades/{unidade['id']}/historico")["itens"]
    assert [e["acao"] for e in eventos].count("unidade.desativada") == 1


def test_a_api_continua_sendo_a_autoridade(gestor: tuple[Page, str]) -> None:
    """Contratos que a tela não substitui: 404 vindo da procedure (SQLSTATE SGS01), 422 de motivo,
    idempotência para unidade inativa e o PATCH que não desativa."""
    pagina, token_ = gestor
    inexistente = requisicao(
        pagina, token_, "POST", f"/unidades/{uuid.uuid4()}/desativar", {"motivo": "Teste"}
    )
    assert inexistente.status == 404  # só a procedure levanta SGS01, que a rota traduz em 404
    unidade = nova_unidade(pagina, token_)
    curto = requisicao(
        pagina, token_, "POST", f"/unidades/{unidade['id']}/desativar", {"motivo": "ab"}
    )
    assert curto.status == 422
    pelo_patch = requisicao(
        pagina,
        token_,
        "PATCH",
        f"/unidades/{unidade['id']}",
        {"status": "inativa"},
        {"If-Match": f'"{unidade["versao"]}"'},
    )
    assert pelo_patch.status == 422  # desativar só pela procedure
    primeira: dict[str, Any] = api(
        pagina, token_, f"/unidades/{unidade['id']}/desativar", "POST", {"motivo": "Primeira"}
    )
    segunda: dict[str, Any] = api(
        pagina, token_, f"/unidades/{unidade['id']}/desativar", "POST", {"motivo": "Segunda"}
    )
    assert segunda["versao"] == primeira["versao"]  # já inativa: nada muda


@pytest.mark.parametrize(
    "papel", ["TECNICO_DISTRITAL", "GESTOR_UNIDADE", "COORD_TECNICO", "DIRETORIA"]
)
def test_so_o_gestor_de_dados_ve_o_botao_e_a_api_nega_os_demais(
    sessao_de: Sessao, papel: str
) -> None:
    pagina = sessao_de(papel)
    token_ = token(pagina)
    unidade_id = api(pagina, token_, "/unidades?tamanho=1")["itens"][0]["id"]
    _abrir(pagina, unidade_id)
    expect(pagina.locator("[data-ref=desativar]")).to_have_count(0)
    negado = requisicao(
        pagina,
        token_,
        "POST",
        f"/unidades/{unidade_id}/desativar",
        {"motivo": "Tentativa indevida"},
    )
    assert negado.status == 403
    assert api(pagina, token_, f"/unidades/{unidade_id}")["status"] != "inativa"


@pytest.mark.parametrize("largura", [1280, 390])
def test_sem_rolagem_horizontal(gestor: tuple[Page, str], largura: int) -> None:
    pagina, token_ = gestor
    pagina.set_viewport_size({"width": largura, "height": 900})
    unidade = nova_unidade(pagina, token_)
    _abrir(pagina, unidade["id"])
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    pagina.click("[data-ref=desativar]")
    expect(pagina.locator("#fd")).to_be_visible()
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
