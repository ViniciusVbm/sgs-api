"""Aparência igual à do protótipo, fonte local e nada externo (spec 012, T2: R1.2, R1.3, R1.5).

A referência são capturas do próprio protótipo (`frontend/prototipo/`, fora do Git), com o Google
Fonts redirecionado para a fonte local, guardadas em `referencia/`. Para regenerá-las a partir do
protótipo: `SGS_ATUALIZAR_REFERENCIA=1 uv run pytest tests/e2e_front/test_aparencia.py -m slow`.

Compara os elementos que a spec manda manter iguais (marca, apresentação e botão principal da tela
de login). O restante do login mudou por requisito: sem contas de demonstração (R2.10) e com o
rótulo "Usuário" (DF7).
"""

import base64
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
from playwright.sync_api import Browser, Page, expect

from tests.e2e_front.conftest import BASE, RAIZ, novo_contexto

PROTOTIPO = RAIZ / "frontend" / "prototipo" / "Prototipo_SGS_Recife_v2.html"
FONTES = RAIZ / "frontend" / "app" / "assets" / "css" / "fonts.css"
REFERENCIA = Path(__file__).parent / "referencia"
LARGURAS = (1280, 860, 390)
# Só elementos de conteúdo: as faixas decorativas do painel acompanham a altura da página, que é
# menor sem as contas de demonstração (R2.10), e não entram na comparação.
ELEMENTOS = {
    "simbolo": ".login-side .brand-mark",
    "nome": ".login-side > div:nth-child(2) > div:nth-child(2)",
    "titulo": ".login-side h1",
    "texto": ".login-side p",
    "fluxo": ".login-side .flow span:first-child",
    "botao": "#loginForm button.btn-primary",
}
LIMIAR = 0.01  # fração máxima de pixels diferentes

_DIFERENCA = """async ([a, b]) => {
  const carregar = (src) => new Promise((ok, falha) => {
    const img = new Image(); img.onload = () => ok(img); img.onerror = falha; img.src = src; });
  const [x, y] = await Promise.all([carregar(a), carregar(b)]);
  if (x.width !== y.width || x.height !== y.height) return 1;
  const pixels = (img) => {
    const c = document.createElement('canvas');
    c.width = img.width; c.height = img.height;
    const g = c.getContext('2d'); g.drawImage(img, 0, 0);
    return g.getImageData(0, 0, img.width, img.height).data;
  };
  const p = pixels(x), q = pixels(y); let diferentes = 0;
  for (let i = 0; i < p.length; i += 4) {
    const d = Math.abs(p[i] - q[i]) + Math.abs(p[i + 1] - q[i + 1]) + Math.abs(p[i + 2] - q[i + 2]);
    if (d > 48) diferentes++;
  }
  return diferentes / (p.length / 4);
}"""


def _abrir_prototipo(pagina: Page) -> None:
    # As URLs da fonte se resolvem contra o CSS servido; aqui elas apontam para o próprio servidor.
    fontes = FONTES.read_text(encoding="utf-8").replace("url('/assets/", f"url('{BASE}/assets/")
    pagina.route(
        f"{BASE}/__prototipo__",
        lambda r: r.fulfill(
            status=200, content_type="text/html", body=PROTOTIPO.read_text(encoding="utf-8")
        ),
    )
    pagina.route(
        "https://fonts.googleapis.com/**",
        lambda r: r.fulfill(status=200, content_type="text/css", body=fontes),
    )
    pagina.route("https://fonts.gstatic.com/**", lambda r: r.abort())
    pagina.goto("/__prototipo__")


ESTILO = (
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "line-height",
    "color",
    "background-color",
    "border-radius",
    "border-top-width",
    "border-top-color",
    "padding-top",
    "padding-left",
    "letter-spacing",
    "text-transform",
)
_MEDIDAS = """(el, props) => {
  const b = el.getBoundingClientRect(); const cs = getComputedStyle(el);
  return {largura: b.width, altura: b.height, fx: b.x % 1, fy: b.y % 1,
          estilo: Object.fromEntries(props.map((p) => [p, cs.getPropertyValue(p)]))}; }"""


def _capturas(pagina: Page) -> dict[str, tuple[bytes, dict[str, Any]]]:
    expect(pagina.locator("#loginForm")).to_be_visible()
    pagina.evaluate("document.fonts.ready")
    # Sem a fonte local carregada, a comparação perderia o sentido (R1.3).
    assert pagina.evaluate("document.fonts.check('16px \"Atkinson Hyperlegible\"')")
    assert pagina.evaluate(
        "[...document.fonts].some(f => f.family.includes('Atkinson') && f.status === 'loaded')"
    )
    capturas = {}
    for nome, seletor in ELEMENTOS.items():
        alvo = pagina.locator(seletor)
        if alvo.is_visible():
            medidas = alvo.evaluate(_MEDIDAS, list(ESTILO))
            capturas[nome] = (alvo.screenshot(animations="disabled"), medidas)
    return capturas


def _url(png: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png).decode()


@pytest.mark.parametrize("largura", LARGURAS)
def test_login_igual_ao_prototipo_e_sem_recurso_externo(
    navegador: Browser, senha_demo: str, largura: int
) -> None:
    contexto = novo_contexto(navegador)
    pagina = contexto.new_page()
    pagina.set_viewport_size({"width": largura, "height": 900})
    origem = urlparse(BASE).netloc
    externas: list[str] = []
    pagina.on(
        "request",
        lambda req: (
            externas.append(req.url)
            if urlparse(req.url).netloc not in (origem, "") and not req.url.startswith("data:")
            else None
        ),
    )

    if os.environ.get("SGS_ATUALIZAR_REFERENCIA") == "1":
        if not PROTOTIPO.exists():
            pytest.skip("protótipo ausente; não há como regenerar a referência")
        ref = contexto.new_page()
        ref.set_viewport_size({"width": largura, "height": 900})
        _abrir_prototipo(ref)
        REFERENCIA.mkdir(exist_ok=True)
        for nome, (png, medidas) in _capturas(ref).items():
            (REFERENCIA / f"{nome}-{largura}.png").write_bytes(png)
            (REFERENCIA / f"{nome}-{largura}.json").write_text(json.dumps(medidas, indent=1) + "\n")

    pagina.goto("/")
    capturas = _capturas(pagina)
    assert externas == []  # R1.3: nada de outro domínio (fontes, CDN)
    # R1.4 (verificado de novo na T13): sem rolagem horizontal da página
    assert pagina.evaluate("document.documentElement.scrollWidth <= window.innerWidth")

    referencias = {p.stem.rsplit("-", 1)[0]: p for p in REFERENCIA.glob(f"*-{largura}.png")}
    assert referencias, "sem capturas de referência; gere com SGS_ATUALIZAR_REFERENCIA=1"
    assert set(capturas) == set(referencias)  # os mesmos elementos visíveis nesta largura
    for nome, (png, medidas) in capturas.items():
        ref = json.loads(referencias[nome].with_suffix(".json").read_text())
        # Mesma caixa e mesmos estilos calculados: é o que garante "sem mudança visual" (R1.2).
        assert abs(medidas["largura"] - ref["largura"]) < 1, nome
        assert abs(medidas["altura"] - ref["altura"]) < 1, nome
        assert medidas["estilo"] == ref["estilo"], nome
        # Pixels: só quando a posição fracionária coincide; frações diferentes mudam o serrilhado
        # do texto sem mudança visual real (ex.: o rodapé do painel, alterado por R2.10).
        if abs(medidas["fx"] - ref["fx"]) < 0.01 and abs(medidas["fy"] - ref["fy"]) < 0.01:
            diferenca = pagina.evaluate(
                _DIFERENCA, [_url(png), _url(referencias[nome].read_bytes())]
            )
            assert diferenca <= LIMIAR, (
                f"{nome} em {largura}px difere em {diferenca:.2%} do protótipo"
            )
    contexto.close()


def test_icones_e_fonte_vem_dos_arquivos_locais(navegador: Browser, senha_demo: str) -> None:
    """R1.3: o sprite de ícones e a fonte carregam do próprio servidor."""
    contexto = novo_contexto(navegador)
    pagina = contexto.new_page()
    respostas: dict[str, int] = {}
    pagina.on("response", lambda r: respostas.__setitem__(urlparse(r.url).path, r.status))
    pagina.goto("/")
    expect(pagina.locator("#loginForm")).to_be_visible()
    pagina.evaluate("document.fonts.ready")
    assert respostas.get("/assets/css/app.css") == 200
    assert respostas.get("/assets/css/fonts.css") == 200
    assert any(p.startswith("/assets/fonts/") and s == 200 for p, s in respostas.items())
    assert pagina.evaluate("document.fonts.check('16px \"Atkinson Hyperlegible\"')")
    contexto.close()
