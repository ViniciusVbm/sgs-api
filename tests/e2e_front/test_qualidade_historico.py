"""Qualidade, histórico geral, log do banco, partições e cadeia (spec 012, T11 parte A:
R12.1 sem as 8 verificações, R12.2, R12.4, R12.5, R12.6).

Toda asserção numérica compara a tela com a resposta da API no mesmo instante, nunca com
número fixo. O único `UPDATE` direto roda no PostgreSQL do compose descartável deste E2E
(design § Dados nos E2E da emenda), para provar o trigger fora da API.
"""

import math
import re
import secrets
from collections.abc import Callable, Iterator
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from playwright.sync_api import Page, Response, Route, expect

from tests.e2e_front.apoio import api as _api
from tests.e2e_front.apoio import token as _token
from tests.e2e_front.conftest import PROJETO, _compose

Sessao = Callable[[str], Page]


def _todas(pagina: Page, token: str, caminho: str, filtros: str = "") -> list[dict[str, Any]]:
    itens: list[dict[str, Any]] = []
    numero = 1
    while True:
        separador = "&" if filtros else ""
        dados = _api(pagina, token, f"{caminho}?{filtros}{separador}pagina={numero}&tamanho=100")
        itens.extend(dados["itens"])
        if len(itens) >= dados["total"] or not dados["itens"]:
            return itens
        numero += 1


def _abrir_qualidade(pagina: Page, consulta: str = "") -> None:
    with pagina.expect_response("**/api/v1/dashboard/consultas"):
        pagina.goto("/#/sem-acesso")
        pagina.goto(f"/#/qualidade{consulta}")
    expect(pagina.locator("[data-ref=indicadores]")).to_be_visible()
    expect(pagina.locator("#q-graficos figure")).to_have_count(4)


def _id_do_distrito(pagina: Page, token: str, codigo: str) -> int:
    distritos = _api(pagina, token, "/referencias/distritos")
    return int(next(d["id"] for d in distritos if d["codigo"] == codigo))


@pytest.fixture
def gestor(sessao_de: Sessao) -> Iterator[tuple[Page, str]]:
    pagina = sessao_de("GESTOR_DADOS")
    yield pagina, _token(pagina)
    pagina.close()


def test_catalogo_inteiro_com_titulo_tecnica_e_justificativa(gestor: tuple[Page, str]) -> None:
    pagina, token = gestor
    catalogo = _api(pagina, token, "/dashboard/consultas")
    _abrir_qualidade(pagina)
    secoes = pagina.locator("#q-consultas details")
    expect(secoes).to_have_count(len(catalogo))
    for entrada in catalogo:
        secao = pagina.locator(f"#q-consultas details[data-consulta='{entrada['nome']}']")
        expect(secao.locator("summary .t-name")).to_have_text(entrada["titulo"])
        expect(secao.locator("[data-ref=tecnica]")).to_have_text(entrada["tecnica_sql"])
        expect(secao.locator("[data-ref=justificativa]")).to_have_text(entrada["justificativa"])
    tecnicas = " ".join(e["tecnica_sql"] for e in catalogo).lower()
    for tecnica in (
        "anti join",
        "full outer join",
        "subconsulta",
        "exists",
        "join de cinco tabelas",
        "view",
    ):
        assert tecnica in tecnicas


def test_totais_das_consultas_com_filtro_do_distrito_iguais_aos_da_api(
    gestor: tuple[Page, str],
) -> None:
    pagina, token = gestor
    ds4 = _id_do_distrito(pagina, token, "DS-IV")
    _abrir_qualidade(pagina)
    with pagina.expect_response("**/api/v1/dashboard/resumo?distrito=*") as filtrado:
        pagina.select_option("#fq-distrito", str(ds4))
    assert f"distrito={ds4}" in pagina.url  # o filtro fica na URL
    geral = _api(pagina, token, "/dashboard/resumo")
    assert filtrado.value.json()["unidades"]["total"] < geral["unidades"]["total"]
    expect(pagina.locator("[data-ref=total] .v")).to_have_text(
        str(filtrado.value.json()["unidades"]["total"])
    )
    catalogo = _api(pagina, token, "/dashboard/consultas")
    executaveis = [
        e for e in catalogo if e["rota"].startswith("/api/v1/dashboard/") and e["nome"] != "resumo"
    ]
    for entrada in executaveis:
        secao = pagina.locator(f"#q-consultas details[data-consulta='{entrada['nome']}']")
        rota: str = entrada["rota"]

        def da_consulta(resposta: Response, rota: str = rota) -> bool:
            return urlparse(resposta.url).path == rota

        with pagina.expect_response(da_consulta) as resposta:
            secao.locator("summary").click()
        parametros = parse_qs(urlparse(resposta.value.url).query)
        if "distrito" in entrada["parametros"]:
            assert parametros["distrito"] == [str(ds4)], entrada["nome"]
        dados = resposta.value.json()
        total = dados["total"] if entrada["paginada"] else len(dados)
        expect(secao.locator("[data-ref=total]")).to_have_attribute("data-total", str(total))
        secao.locator("summary").click()  # fecha, para não recarregar nos próximos filtros


def test_filtro_inexistente_mostra_o_erro_da_api(gestor: tuple[Page, str]) -> None:
    pagina, _ = gestor
    with pagina.expect_response("**/api/v1/dashboard/resumo?distrito=9999") as resposta:
        pagina.goto("/#/sem-acesso")
        pagina.goto("/#/qualidade?distrito=9999")
    assert resposta.value.status == 422
    expect(pagina.locator("#q-indicadores [data-estado=erro]")).to_contain_text(
        resposta.value.json()["detail"]
    )


def test_medias_somam_todas_as_paginas_do_inventario(gestor: tuple[Page, str]) -> None:
    pagina, token = gestor
    linhas = _todas(pagina, token, "/dashboard/inventario")
    pedidos: list[str] = []

    def pagina_pequena(rota: Route) -> None:  # força várias páginas: a média não pode usar só a 1ª
        pedidos.append(rota.request.url)
        rota.continue_(url=re.sub(r"tamanho=\d+", "tamanho=7", rota.request.url))

    pagina.route("**/api/v1/dashboard/inventario?*", pagina_pequena)
    try:
        _abrir_qualidade(pagina)
        medias = pagina.locator("[data-ref=medias]")
        expect(medias).to_have_attribute("data-n", str(len(linhas)))
    finally:
        pagina.unroute("**/api/v1/dashboard/inventario?*")
    assert len(pedidos) == math.ceil(len(linhas) / 7)
    esperado_servicos = sum(u["service_count"] for u in linhas) / len(linhas)
    esperado_equipamentos = sum(u["equipment_count"] for u in linhas) / len(linhas)
    assert float(medias.get_attribute("data-media-servicos") or "nan") == pytest.approx(
        esperado_servicos
    )
    assert float(medias.get_attribute("data-media-equipamentos") or "nan") == pytest.approx(
        esperado_equipamentos
    )


def test_pizza_percentual_da_rede_e_tendencia_vem_da_api(gestor: tuple[Page, str]) -> None:
    pagina, token = gestor
    _abrir_qualidade(pagina)
    for situacao in ("regular", "sem_cnes", "com_pendencias", "inativa"):
        total = _api(pagina, token, f"/dashboard/inventario?situacao={situacao}&tamanho=1")["total"]
        expect(
            pagina.locator(f"[data-ref=grafico-situacao] [data-fatia={situacao}] b")
        ).to_have_text(str(total))
    acima = _api(pagina, token, "/dashboard/consultas/distritos-sem-cnes-acima-da-rede")["itens"]
    if acima:
        rede = (
            f"{acima[0]['network_percent_without_cnes']:.2f}".replace(".", ",")
            .rstrip("0")
            .rstrip(",")
        )
        expect(pagina.locator("[data-ref=grafico-cnes] .viz-nota")).to_contain_text(f"{rede}%")
    alteracoes = _api(pagina, token, "/dashboard/consultas/alteracoes-por-periodo")
    ritmo = pagina.locator("[data-ref=ritmo]")
    assert float(ritmo.get_attribute("data-r7") or "nan") == pytest.approx(
        sum(a["last_7_days"] for a in alteracoes) / 7
    )
    assert float(ritmo.get_attribute("data-r30") or "nan") == pytest.approx(
        sum(a["last_30_days"] for a in alteracoes) / 30
    )


def test_graficos_sao_svg_acessiveis_com_os_dados_da_api(gestor: tuple[Page, str]) -> None:
    pagina, token = gestor
    _abrir_qualidade(pagina)
    for ref in ("grafico-situacao", "grafico-cnes", "grafico-alteracoes", "grafico-equipamentos"):
        figura = pagina.locator(f"[data-ref={ref}]")
        if figura.locator("[data-estado=vazio]").count():
            continue
        expect(figura.locator("svg[role=img]")).to_have_count(1)
        assert figura.locator("svg[role=img]").get_attribute("aria-label")
    alteracoes = _api(pagina, token, "/dashboard/consultas/alteracoes-por-periodo")
    dados = pagina.locator("[data-ref=grafico-alteracoes] .viz-dados")
    dados.locator("summary").click()
    expect(dados.locator("tbody tr")).to_have_count(len(alteracoes))


def test_linha_do_periodo_soma_todas_as_paginas_e_preenche_zeros(gestor: tuple[Page, str]) -> None:
    pagina, token = gestor
    pedidos: list[str] = []

    def pagina_pequena(rota: Route) -> None:
        pedidos.append(rota.request.url)
        rota.continue_(url=re.sub(r"tamanho=\d+", "tamanho=25", rota.request.url))

    pagina.route("**/api/v1/auditoria/banco?*", pagina_pequena)
    try:
        _abrir_qualidade(pagina)
        grafico = pagina.locator("[data-ref=grafico-linha]")
        expect(grafico).to_be_visible()
    finally:
        pagina.unroute("**/api/v1/auditoria/banco?*")
    consulta = parse_qs(urlparse(pedidos[0]).query)
    de, ate = consulta["de"][0], consulta["ate"][0]
    no_periodo = _api(
        pagina,
        token,
        f"/auditoria/banco?de={de.replace('+', '%2B')}&ate={ate.replace('+', '%2B')}&tamanho=1",
    )["total"]
    assert len(pedidos) == max(1, math.ceil(no_periodo / 25))
    expect(grafico).to_have_attribute("data-total", str(no_periodo))
    grafico.locator(".viz-dados summary").click()
    linhas = grafico.locator(".viz-dados tbody tr")
    expect(linhas).to_have_count(7)  # 7 dias, por dia, com zero nos dias sem registro
    valores = [int(v) for v in linhas.locator("td:nth-child(2)").all_inner_texts()]
    assert sum(valores) == no_periodo
    aviso = pagina.locator("[data-ref=historico-insuficiente]")
    expect(aviso).to_have_count(1 if sum(1 for v in valores if v) < 2 else 0)

    with pagina.expect_response("**/api/v1/auditoria/banco?*"):
        pagina.click("#fp [data-periodo='30']")
    expect(pagina.locator("[data-ref=grafico-linha] .viz-dados tbody tr")).to_have_count(30)
    assert "periodo=30" in pagina.url

    hoje = pagina.locator("#fp-de").get_attribute("max")
    pagina.click("#fp [data-periodo=personalizado]")
    pagina.fill("#fp-de", hoje or "")
    pagina.fill("#fp-ate", hoje or "")
    with pagina.expect_response("**/api/v1/auditoria/banco?*"):
        pagina.click("#fp button[type=submit]")
    expect(pagina.locator("[data-ref=grafico-linha] .viz-dados tbody tr")).to_have_count(
        24
    )  # até 2 dias: por hora
    expect(pagina.locator("[data-ref=grafico-linha] figcaption b")).to_contain_text("por hora")


def test_log_do_banco_mostra_alteracao_feita_fora_da_api(gestor: tuple[Page, str]) -> None:
    pagina, token = gestor
    assert PROJETO == "sgs-api-e2e-front-ui", (
        "o UPDATE direto só pode rodar no banco descartável do E2E"
    )
    unidade = _api(pagina, token, "/unidades?tamanho=1")["itens"][0]
    original = unidade["telefone"]
    novo = "8133330000" if original != "8133330000" else "8133330001"

    def sql(comando: str) -> None:
        _compose(
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "sgs",
            "-d",
            "sgs",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            comando,
        )

    # Valores da própria API (UUID) e literais fixos; só no banco descartável do E2E.

    sql(f"UPDATE health_units SET phone = '{novo}' WHERE id = '{unidade['id']}'")  # noqa: S608
    try:
        pagina.goto("/#/sem-acesso")
        with pagina.expect_response("**/api/v1/auditoria/banco?*fora_da_api=true*") as resposta:
            pagina.goto("/#/historico?aba=banco&fora_da_api=true")
        dados = resposta.value.json()
        assert dados["total"] >= 1
        assert all(not r["pela_api"] for r in dados["itens"])
        linha = pagina.locator(f"tr[data-linha='{unidade['id']}']").first
        expect(linha.locator("[data-ref=origem]")).to_have_text("fora da API")
        expect(linha).to_contain_text(novo)
        expect(pagina.locator("[data-ref=origem-log]")).to_contain_text("trg_registry_change_log")
        with pagina.expect_response("**/api/v1/auditoria/banco?*fora_da_api=false*") as todos:
            pagina.uncheck("#fb-fora")
        assert todos.value.json()["total"] > dados["total"]
        expect(pagina.locator("[data-ref=origem]", has_text="pela API").first).to_be_visible()
    finally:
        restaurar = "NULL" if original is None else f"'{original}'"
        sql(f"UPDATE health_units SET phone = {restaurar} WHERE id = '{unidade['id']}'")  # noqa: S608


def test_particoes_criadas_pelo_procedimento(gestor: tuple[Page, str]) -> None:
    pagina, token = gestor
    particoes = _api(pagina, token, "/auditoria/banco/particoes")
    pagina.goto("/#/sem-acesso")
    pagina.goto("/#/historico?aba=particoes")
    expect(pagina.locator("[data-particao]")).to_have_count(len(particoes))
    expect(pagina.locator("[data-ref=origem-particoes]")).to_contain_text(
        "sp_ensure_monthly_partitions"
    )


def test_trilha_filtra_por_periodo_e_autor(gestor: tuple[Page, str]) -> None:
    pagina, token = gestor
    # Evento com autor criado pelo teste (banco descartável): o seed grava eventos sem autor.
    codigo = f"E2E_TRILHA_{secrets.token_hex(3).upper()}"
    _api(
        pagina,
        token,
        "/referencias/tipos-servico",
        "POST",
        {"codigo": codigo, "nome": f"Tipo de teste {codigo}"},
    )
    pagina.goto("/#/sem-acesso")
    with pagina.expect_response("**/api/v1/auditoria/eventos?*") as primeira:
        pagina.goto("/#/historico")
    evento = next(e for e in primeira.value.json()["itens"] if e["autor"]["id"])
    with pagina.expect_request("**/api/v1/auditoria/eventos?*") as pedido:
        pagina.locator(f"[data-autor='{evento['autor']['id']}']").first.click()
    assert f"autor={evento['autor']['id']}" in pedido.value.url
    hoje = evento["quando"][:10]
    pagina.fill("#ft-de", hoje)
    pagina.fill("#ft-ate", hoje)
    with pagina.expect_request("**/api/v1/auditoria/eventos?*") as pedido:
        pagina.click("#ft button[type=submit]")
    consulta = parse_qs(urlparse(pedido.value.url).query)
    assert consulta["de"]
    assert consulta["ate"]
    assert consulta["autor"] == [evento["autor"]["id"]]


def test_auditor_ve_a_cadeia_integra(sessao_de: Sessao) -> None:
    pagina = sessao_de("AUDITOR")
    pagina.goto("/#/cadeia")
    with pagina.expect_response("**/api/v1/auditoria/verificar") as resposta:
        pagina.click("#verificar")
    assert resposta.value.json()["integra"] is True
    expect(pagina.locator("[data-ref=resultado-cadeia]")).to_have_attribute("data-integra", "true")


def test_escopo_menor_e_sem_auditoria_nao_veem_log_nem_linha(sessao_de: Sessao) -> None:
    tecnico = sessao_de("TECNICO_DISTRITAL")
    pedidos: list[str] = []
    tecnico.on("request", lambda r: pedidos.append(r.url))
    _abrir_qualidade(tecnico)
    expect(tecnico.locator("#q-periodo")).to_have_count(0)
    tecnico.goto("/#/historico")
    expect(tecnico.locator("[data-estado=em-desenvolvimento]")).to_be_visible()
    assert not any("/auditoria/banco" in u for u in pedidos)

    diretoria = sessao_de("DIRETORIA")
    _abrir_qualidade(diretoria)
    expect(diretoria.locator("#q-periodo")).to_have_count(0)
    diretoria.goto("/#/historico")
    expect(diretoria.locator("[data-estado=sem-acesso]")).to_be_visible()


def test_links_do_inicio_e_das_consultas_que_nao_rodam_no_painel(gestor: tuple[Page, str]) -> None:
    pagina, _ = gestor
    pagina.goto("/#/inicio")
    pagina.click("[data-ref=painel-completo]")
    expect(pagina.locator("[data-ref=indicadores]")).to_be_visible()
    historico = pagina.locator("#q-consultas details[data-consulta='historico-da-unidade']")
    historico.locator("summary").click()
    expect(historico.locator("a[href='#/unidades']")).to_be_visible()
    log = pagina.locator("#q-consultas details[data-consulta='log-do-banco']")
    log.locator("summary").click()
    expect(log.locator("[data-ref=link-historico]")).to_have_attribute(
        "href", "#/historico?aba=banco"
    )


@pytest.mark.parametrize("largura", [1280, 390])
def test_sem_rolagem_horizontal(gestor: tuple[Page, str], largura: int) -> None:
    pagina, _ = gestor
    pagina.set_viewport_size({"width": largura, "height": 900})
    _abrir_qualidade(pagina)
    expect(pagina.locator("[data-ref=grafico-linha]")).to_be_visible()
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    for aba in ("trilha", "banco", "particoes"):
        pagina.goto(f"/#/historico?aba={aba}")
        expect(pagina.locator("#h-corpo [data-ref=total]")).to_be_visible()
        assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), aba


# --- Spec 013, T14: detalhe do evento, resultado, horário e verificação com âncora


def _abrir_trilha(pagina: Page) -> dict[str, Any]:
    pagina.goto("/#/sem-acesso")
    with pagina.expect_response("**/api/v1/auditoria/eventos?*") as lista:
        pagina.goto("/#/historico")
    dados: dict[str, Any] = lista.value.json()
    return dados


def _abrir_detalhe(pagina: Page, evento: int) -> dict[str, Any]:
    with pagina.expect_response(f"**/api/v1/auditoria/eventos/{evento}") as resposta:
        pagina.locator(f"[data-detalhe='{evento}']").click()
    expect(pagina.locator("[role=dialog] [data-ref=detalhe-evento]")).to_be_visible()
    dados: dict[str, Any] = resposta.value.json()
    return dados


def test_detalhe_do_evento_auditor(sessao_de: Sessao) -> None:
    """013/R8.1, R8.2, R2.2: o Auditor abre o evento e vê o instante ISO, o resultado, o hash e a
    origem como a API devolveu."""
    pagina = sessao_de("AUDITOR")
    [primeiro, *_] = _abrir_trilha(pagina)["itens"]

    evento = _abrir_detalhe(pagina, primeiro["id"])

    caixa = pagina.locator("[role=dialog]")
    assert evento["origem_restrita"] is False
    expect(caixa.locator("[data-ref=detalhe-evento]")).to_have_attribute(
        "data-origem-restrita", "false"
    )
    expect(caixa.locator("[data-ref=instante]")).to_have_text(evento["quando"])
    expect(caixa.locator("[data-ref=hash]")).to_have_text(evento["hash"])
    expect(caixa.locator("[data-ref=ip]")).to_have_text(evento["ip"] or "não registrado")
    expect(caixa.locator("[data-ref=restrito]")).to_have_count(0)


def test_detalhe_restrito_gestor_dados(gestor: tuple[Page, str]) -> None:
    """013/R8.2: para o Gestor de Dados, a API não manda IP, User-Agent nem sessão, e a tela diz
    que são restritos ao Auditor."""
    pagina, _ = gestor
    [primeiro, *_] = _abrir_trilha(pagina)["itens"]

    evento = _abrir_detalhe(pagina, primeiro["id"])

    caixa = pagina.locator("[role=dialog]")
    assert (evento["ip"], evento["user_agent"], evento["sessao_id"]) == (None, None, None)
    assert evento["origem_restrita"] is True
    for campo in ("ip", "user-agent", "sessao"):
        expect(caixa.locator(f"[data-ref={campo}]")).to_have_text("restrito ao Auditor")


def test_evento_antigo_mostra_nao_registrado(gestor: tuple[Page, str]) -> None:
    """013/R1.5: um evento anterior à 013 vem sem tipo, origem e resultado; a tela mostra "não
    registrado". O banco do E2E nasce já no head das migrações, então a resposta da lista é
    alterada aqui para simular o evento antigo."""
    pagina, _ = gestor

    def antigo(rota: Route) -> None:
        resposta = rota.fetch()
        dados = resposta.json()
        for item in dados["itens"][:1]:
            item.update({"origem": None, "resultado": None, "resultado_categoria": None})
            item["autor"]["tipo"] = None
        rota.fulfill(response=resposta, json=dados)

    pagina.route("**/api/v1/auditoria/eventos?*", antigo)
    try:
        _abrir_trilha(pagina)
        chip = pagina.locator("tbody tr").first.locator("[data-ref=resultado]")
        expect(chip).to_have_text("não registrado")
        expect(chip).to_have_attribute("data-resultado", "")
    finally:
        pagina.unroute("**/api/v1/auditoria/eventos?*")


def test_horario_com_segundos_e_fuso(gestor: tuple[Page, str]) -> None:
    """013/R2.1: trilha e log do banco com segundos e o fuso explícito."""
    pagina, _ = gestor
    # O sinal do fuso é o MENOS (U+2212) do rótulo da tela (`ROTULO_DO_FUSO`, ui/format.js).
    formato = re.compile(r"\d{2}/\d{2}/\d{4},? \d{2}:\d{2}:\d{2} \(UTC" + "\u2212" + r"03:00\)")
    _abrir_trilha(pagina)
    expect(pagina.locator("tbody tr").first.locator("td").first).to_have_text(formato)

    with pagina.expect_response("**/api/v1/auditoria/banco?*"):
        pagina.goto("/#/historico?aba=banco")
    expect(pagina.locator("tbody tr").first.locator("td").first).to_have_text(formato)


def test_cadeia_mostra_cabeca_cadeia_e_ancora(sessao_de: Sessao) -> None:
    """013/R8.3: a verificação mostra o fim conferido com a cabeça; com a âncora (o primeiro
    evento e o último verificado), a cadeia e a âncora conferem; com um hash errado, não."""
    pagina = sessao_de("AUDITOR")
    token = _token(pagina)
    total = _api(pagina, token, "/auditoria/eventos?tamanho=1")["total"]
    [primeiro] = _api(pagina, token, f"/auditoria/eventos?tamanho=1&pagina={total}")["itens"]
    cadeia_id = _api(pagina, token, f"/auditoria/eventos/{primeiro['id']}")["hash"]
    pagina.goto("/#/cadeia")

    with pagina.expect_response("**/api/v1/auditoria/verificar") as sem_ancora:
        pagina.click("#verificar")
    r = sem_ancora.value.json()
    expect(pagina.locator("[data-ref=cabeca-confere]")).to_have_attribute("data-valor", "true")
    expect(pagina.locator("[data-ref=ancora-confere]")).to_have_attribute("data-valor", "null")
    expect(pagina.locator("[data-ref=ultimo-id]")).to_have_text(str(r["ultimo_id"]))

    pagina.fill("#ancora-cadeia", cadeia_id)
    pagina.fill("#ancora-id", str(r["ultimo_id"]))
    pagina.fill("#ancora-hash", r["hash_final"])
    with pagina.expect_response("**/api/v1/auditoria/verificar"):
        pagina.click("#verificar")
    expect(pagina.locator("[data-ref=resultado-cadeia]")).to_have_attribute("data-integra", "true")
    expect(pagina.locator("[data-ref=cadeia-confere]")).to_have_attribute("data-valor", "true")
    expect(pagina.locator("[data-ref=ancora-confere]")).to_have_attribute("data-valor", "true")

    pagina.fill("#ancora-hash", "0" * 64)
    with pagina.expect_response("**/api/v1/auditoria/verificar"):
        pagina.click("#verificar")
    expect(pagina.locator("[data-ref=resultado-cadeia]")).to_have_attribute("data-integra", "false")
    expect(pagina.locator("[data-ref=ancora-confere]")).to_have_attribute("data-valor", "false")
