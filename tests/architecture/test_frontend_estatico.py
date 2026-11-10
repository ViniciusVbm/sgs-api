"""Regras estáticas do front (spec 012: T3 e T4; R2.10, R15.1, R15.3, R15.4, R1.3).

Lê os arquivos de `frontend/app` sem navegador nem dependência nova. O escape real é provado
pelos E2E de XSS (T13); aqui ficam as garantias que um grep consegue dar.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "frontend" / "app"
JS = sorted((APP / "js").rglob("*.js"))
TEXTO = sorted([*JS, *APP.rglob("*.html"), *(APP / "assets").rglob("*.css")])


def _sem_comentarios(codigo: str) -> str:
    codigo = re.sub(r"/\*.*?\*/", "", codigo, flags=re.S)
    return re.sub(r"(?m)^\s*//.*$|(?<=[;{}),\s])//[^\n'\"`]*$", "", codigo)


def _rel(caminho: Path) -> str:
    return str(caminho.relative_to(RAIZ))


def test_o_front_tem_modulos_js() -> None:
    assert JS, "frontend/app/js está vazio"


@pytest.mark.parametrize("arquivo", JS, ids=_rel)
def test_sem_eval_nem_new_function(arquivo: Path) -> None:
    """R15.4"""
    codigo = _sem_comentarios(arquivo.read_text(encoding="utf-8"))
    assert not re.search(r"\beval\s*\(", codigo)
    assert not re.search(r"\bnew\s+Function\b", codigo)
    assert not re.search(r"\bsetTimeout\s*\(\s*['\"`]", codigo)
    assert "document.write" not in codigo


@pytest.mark.parametrize("arquivo", JS, ids=_rel)
def test_html_so_entra_pelo_montar(arquivo: Path) -> None:
    """R15.1, R15.4: o único `innerHTML` é o de `montar()`, que recusa texto sem escape."""
    codigo = _sem_comentarios(arquivo.read_text(encoding="utf-8"))
    escritas = re.findall(r"\.(innerHTML|outerHTML)\s*=|insertAdjacentHTML\s*\(", codigo)
    if arquivo.name == "html.js":
        assert escritas == ["innerHTML"]
        assert "if (!(conteudo instanceof Confiavel)) throw" in codigo
    else:
        assert escritas == [], f"{_rel(arquivo)} escreve HTML fora de montar()"
    # Handlers inline seriam bloqueados pela CSP (script-src 'self') e misturam código e HTML.
    assert not re.search(r"\son[a-z]+\s*=\s*[\"']", codigo), f"{_rel(arquivo)} tem handler inline"


@pytest.mark.parametrize("arquivo", JS, ids=_rel)
def test_local_storage_so_guarda_o_tema(arquivo: Path) -> None:
    """R15.3: nada de token nem dado de negócio no navegador."""
    codigo = _sem_comentarios(arquivo.read_text(encoding="utf-8"))
    if arquivo.name == "tema.js":
        assert re.findall(r"localStorage\.(\w+)", codigo) == ["setItem", "getItem"]
        assert "localStorage.setItem(CHAVE, tema)" in codigo
    else:
        assert "localStorage" not in codigo
    assert "sessionStorage" not in codigo
    assert "indexedDB" not in codigo
    assert "document.cookie" not in codigo


@pytest.mark.parametrize("arquivo", TEXTO, ids=_rel)
def test_sem_segredos_nem_dados_de_demonstracao(arquivo: Path) -> None:
    """R2.10: nenhum usuário, senha ou código de demonstração do protótipo."""
    texto = arquivo.read_text(encoding="utf-8")
    for proibido in ("DEMO_PASS", "DEMO_CODE", "recife2026", "246810", "resetDemo", "seed()"):
        assert proibido not in texto, f"{_rel(arquivo)} contém {proibido!r}"
    assert not re.search(r"\bUSERS\s*=", texto)


@pytest.mark.parametrize("arquivo", TEXTO, ids=_rel)
def test_nenhum_recurso_de_outro_dominio(arquivo: Path) -> None:
    """R1.3: tudo vem do mesmo domínio; nada de CDN nem Google Fonts."""
    texto = arquivo.read_text(encoding="utf-8")
    externos = [
        url
        for url in re.findall(r"(?:https?:)?//[\w.-]+\.[a-z]{2,}[^\s'\"`)]*", texto)
        if not url.startswith("http://www.w3.org/")
    ]
    assert externos == [], f"{_rel(arquivo)} referencia {externos}"


def test_index_carrega_so_modulo_local() -> None:
    """R15.2: sem script inline (a CSP só permite 'self') e com o módulo principal."""
    index = (APP / "index.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script\b([^>]*)>(.*?)</script>", index, flags=re.S)
    assert scripts == [(' type="module" src="/js/main.js"', "")]
    assert re.search(r"\son\w+\s*=", index) is None
