"""Autenticação pela interface (spec 012, T4: R2.1 a R2.8, R2.10, R2.11, R15.3)."""

import json
import re
from collections.abc import Callable

from playwright.sync_api import Page, Route, expect

from tests.e2e_front.conftest import USUARIOS, Autenticador, entrar, preencher_login

ME_FICTICIO: dict[str, object] = {
    "id": "00000000-0000-7000-8000-000000000001",
    "username": "dev.sem.mfa",
    "nome": "Pessoa de Desenvolvimento",
    "email": None,
    "origem": "local",
    "papeis": [],
    "permissoes": {},
}


def _armazenamento(pagina: Page) -> dict[str, list[str]]:
    resultado: dict[str, list[str]] = pagina.evaluate(
        "() => ({local: Object.keys(localStorage), sessao: Object.keys(sessionStorage)})"
    )
    return resultado


def test_primeiro_acesso_cadastra_o_2fa_em_texto_e_entra(
    pagina_anonima: Page, senha_demo: str, autenticador: Autenticador
) -> None:
    """R2.1, R2.2 (DF6, DF7), R2.3, R15.3"""
    pagina = pagina_anonima
    usuario = USUARIOS["DIRETORIA"]
    pagina.goto("/")
    expect(pagina.get_by_label("Usuário")).to_be_visible()  # DF7
    preencher_login(pagina, usuario, senha_demo)

    chave = pagina.locator("#lg-key")
    uri = pagina.locator("#lg-uri")
    expect(chave).to_be_visible()
    assert uri.input_value().startswith("otpauth://totp/")
    assert f"secret={chave.input_value()}" in uri.input_value()
    assert pagina.locator(".login-box img, .login-box canvas").count() == 0  # sem QR Code (DF6)

    autenticador.segredos[usuario] = chave.input_value()
    pagina.fill("#lg-code", autenticador.codigo(usuario))
    expect(pagina.locator(".shell")).to_be_visible()
    expect(pagina.locator("[data-ref=nome]")).to_have_text(re.compile("Yara Duarte"))
    assert _armazenamento(pagina) == {"local": ["sgs-theme"], "sessao": []}  # só o tema (R15.3)


def test_senha_errada_mostra_a_mensagem_da_api(pagina_anonima: Page) -> None:
    """R2.7"""
    pagina = pagina_anonima
    pagina.goto("/")
    pagina.fill("#lg-user", USUARIOS["AUDITOR"])
    pagina.fill("#lg-pass", "senha-errada-de-proposito")
    with pagina.expect_response("**/api/v1/auth/login") as resposta:
        pagina.click("#loginForm button[type=submit]")
    assert resposta.value.status in (401, 429)
    detalhe = resposta.value.json()["detail"]
    expect(pagina.locator(".err-summary")).to_have_text(detalhe)
    expect(pagina.locator("#lg-code")).to_have_count(0)


def test_login_limitado_mostra_o_aviso_da_api(pagina_anonima: Page) -> None:
    """R2.7: o 429 vem da API; aqui ele é forçado para não gastar o limite real."""
    pagina = pagina_anonima
    corpo = {
        "title": "Too Many Requests",
        "status": 429,
        "detail": "Muitas tentativas de login. Aguarde um minuto.",
    }
    pagina.route(
        "**/api/v1/auth/login",
        lambda rota: rota.fulfill(
            status=429, content_type="application/problem+json", body=json.dumps(corpo)
        ),
    )
    pagina.goto("/")
    pagina.fill("#lg-user", "qualquer")
    pagina.fill("#lg-pass", "qualquer")
    pagina.click("#loginForm button[type=submit]")
    expect(pagina.locator(".err-summary")).to_have_text(str(corpo["detail"]))


def test_login_sem_2fa_em_dev_entra_direto(pagina_anonima: Page) -> None:
    """R2.11: com MFA_OBRIGATORIO=false (só em dev) a API devolve o token no login."""
    pagina = pagina_anonima
    login = {
        "mfa_required": False,
        "mfa_enrollment_required": False,
        "mfa_token": None,
        "access_token": "token-de-dev",
        "expires_in": 900,
    }
    vistos: list[str] = []

    def me(rota: Route) -> None:
        vistos.append(rota.request.headers.get("authorization", ""))
        rota.fulfill(status=200, content_type="application/json", body=json.dumps(ME_FICTICIO))

    pagina.route(
        "**/api/v1/auth/login",
        lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(login)),
    )
    pagina.route("**/api/v1/me", me)
    pagina.goto("/")
    preencher_login(pagina, "dev.sem.mfa", "qualquer")
    expect(pagina.locator(".shell")).to_be_visible()
    expect(pagina.locator("#lg-code")).to_have_count(0)
    assert vistos == ["Bearer token-de-dev"]


def test_recarregar_mantem_a_sessao_pelo_refresh(sessao_de: Callable[[str], Page]) -> None:
    """R2.4"""
    pagina = sessao_de("GESTOR_DADOS")
    with pagina.expect_response("**/api/v1/auth/refresh") as refresh:
        pagina.reload()
    assert refresh.value.status == 200
    assert refresh.value.request.headers["x-requested-with"] == "sgs"
    expect(pagina.locator(".shell")).to_be_visible()


def test_401_renova_a_sessao_e_repete_a_chamada_uma_vez(sessao_de: Callable[[str], Page]) -> None:
    """R2.5: o primeiro /me devolve 401; a interface renova e repete, sem voltar ao login."""
    pagina = sessao_de("GESTOR_DADOS")
    chamadas = {"me": 0, "refresh": 0}

    def me(rota: Route) -> None:
        chamadas["me"] += 1
        if chamadas["me"] == 1:
            rota.fulfill(
                status=401,
                content_type="application/problem+json",
                body='{"detail": "Token expirado."}',
            )
        else:
            rota.continue_()

    def refresh(rota: Route) -> None:
        chamadas["refresh"] += 1
        rota.continue_()

    pagina.route("**/api/v1/me", me)
    pagina.route("**/api/v1/auth/refresh", refresh)
    pagina.reload()
    expect(pagina.locator(".shell")).to_be_visible()
    assert chamadas == {"me": 2, "refresh": 2}  # o da abertura e o da repetição


def test_esqueci_a_senha_orienta_procurar_o_administrador(pagina_anonima: Page) -> None:
    """R2.8"""
    pagina = pagina_anonima
    pagina.goto("/")
    pagina.click("#lg-forgot")
    expect(pagina.locator(".toast")).to_contain_text("Administrador de TI")


def test_sair_com_access_token_valido_encerra_a_sessao_na_api(
    pagina_anonima: Page, senha_demo: str, autenticador: Autenticador
) -> None:
    """R2.6: logout com access token válido; depois de sair, recarregar não recupera a sessão."""
    pagina = pagina_anonima
    entrar(pagina, USUARIOS["DIRETORIA"], senha_demo, autenticador)
    with pagina.expect_response("**/api/v1/auth/logout") as saida:
        pagina.click("#logoutBtn")
    assert saida.value.status == 204
    expect(pagina.locator("#lg-user")).to_be_visible()
    with pagina.expect_response("**/api/v1/auth/refresh") as refresh:
        pagina.reload()
    assert refresh.value.status == 401
    expect(pagina.locator("#lg-user")).to_be_visible()


class _Contador:
    def __init__(self) -> None:
        self.chamadas: dict[str, int] = {"logout": 0, "refresh": 0}

    def contar(self, nome: str) -> Callable[[Route], None]:
        def tratar(rota: Route) -> None:
            self.chamadas[nome] += 1
            rota.continue_()

        return tratar


def _recarregar_sem_sessao(pagina: Page) -> None:
    pagina.unroute_all()
    with pagina.expect_response("**/api/v1/auth/refresh") as refresh:
        pagina.reload()
    assert refresh.value.status == 401
    expect(pagina.locator("#lg-user")).to_be_visible()
    expect(pagina.locator(".shell")).to_have_count(0)


def test_sair_com_access_token_expirado_renova_e_encerra_a_sessao(
    pagina_anonima: Page, senha_demo: str, autenticador: Autenticador
) -> None:
    """R2.6: o primeiro logout recebe 401 (access token expirado; a resposta é forçada no teste);
    a interface renova pelo refresh real, repete o logout uma vez e a sessão acaba na API."""
    pagina = pagina_anonima
    entrar(pagina, USUARIOS["COORD_TECNICO"], senha_demo, autenticador)
    contador = _Contador()
    expirado = {"forcado": False}

    def logout(rota: Route) -> None:
        contador.chamadas["logout"] += 1
        if not expirado["forcado"]:
            expirado["forcado"] = True
            rota.fulfill(
                status=401,
                content_type="application/problem+json",
                body='{"detail": "Token expirado."}',
            )
        else:
            rota.continue_()

    pagina.route("**/api/v1/auth/logout", logout)
    pagina.route("**/api/v1/auth/refresh", contador.contar("refresh"))
    with pagina.expect_response(lambda r: r.url.endswith("/auth/logout") and r.status == 204):
        pagina.click("#logoutBtn")
    expect(pagina.locator("#lg-user")).to_be_visible()
    assert contador.chamadas == {"logout": 2, "refresh": 1}
    _recarregar_sem_sessao(pagina)


def test_sair_com_refresh_invalido_nao_deixa_sessao_restauravel(
    pagina_anonima: Page, senha_demo: str, autenticador: Autenticador
) -> None:
    """R2.6: sem refresh válido (cookie apagado), não há sessão a restaurar; não há repetição."""
    pagina = pagina_anonima
    entrar(pagina, USUARIOS["COORD_TECNICO"], senha_demo, autenticador)
    pagina.context.clear_cookies()  # o refresh deixa de valer
    contador = _Contador()

    def logout(rota: Route) -> None:
        contador.chamadas["logout"] += 1
        rota.fulfill(status=401, content_type="application/problem+json", body="{}")

    pagina.route("**/api/v1/auth/logout", logout)
    pagina.route("**/api/v1/auth/refresh", contador.contar("refresh"))
    pagina.click("#logoutBtn")
    expect(pagina.locator("#lg-user")).to_be_visible()
    pagina.wait_for_timeout(1000)
    assert contador.chamadas == {"logout": 1, "refresh": 1}
    expect(pagina.locator(".toast.err")).to_have_count(0)
    _recarregar_sem_sessao(pagina)


def test_sair_sem_confirmacao_da_api_avisa_e_nao_entra_em_laco(
    pagina_anonima: Page, senha_demo: str, autenticador: Autenticador
) -> None:
    """R2.6: se o logout recusa sempre, há uma única renovação e uma única repetição, e a
    interface avisa que não confirmou o encerramento (sem mostrar sessão autenticada)."""
    pagina = pagina_anonima
    entrar(pagina, USUARIOS["COORD_TECNICO"], senha_demo, autenticador)
    contador = _Contador()

    def logout(rota: Route) -> None:
        contador.chamadas["logout"] += 1
        rota.fulfill(status=401, content_type="application/problem+json", body="{}")

    pagina.route("**/api/v1/auth/logout", logout)
    pagina.route("**/api/v1/auth/refresh", contador.contar("refresh"))
    pagina.click("#logoutBtn")
    expect(pagina.locator("#lg-user")).to_be_visible()
    expect(pagina.locator(".toast.err")).to_contain_text("Não foi possível confirmar")
    pagina.wait_for_timeout(1500)
    assert contador.chamadas == {"logout": 2, "refresh": 1}
    expect(pagina.locator(".shell")).to_have_count(0)
    # Era o caso do aviso: sem a revogação pela API, o refresh ainda restaura a sessão.
    pagina.unroute_all()
    pagina.reload()
    expect(pagina.locator(".shell")).to_be_visible()
    # Limpeza: agora o logout real revoga a sessão.
    pagina.click("#logoutBtn")
    expect(pagina.locator("#lg-user")).to_be_visible()
    _recarregar_sem_sessao(pagina)
