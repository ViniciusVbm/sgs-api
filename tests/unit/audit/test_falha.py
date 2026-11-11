"""Metadados do `operacao.falhou` em lista fechada (spec 013, T6; R4.4, R4.5)."""

import pytest

from src.modules.audit.domain.falha import CODIGOS, categoria_de, metadados_de_falha


def test_metadados_recusam_chave_fora_da_lista() -> None:
    """013/R4.4: só método, rota, status, código e campos; leitura, código desconhecido e rota que
    não seja template são recusados."""
    metadados = metadados_de_falha(
        metodo="PATCH", rota="/api/v1/unidades/{id}", status=412, codigo="precondicao_falhou"
    )

    assert set(metadados) == {"metodo", "rota", "status", "codigo", "campos"}
    with pytest.raises(ValueError, match="escrita"):
        metadados_de_falha(metodo="GET", rota="/api/v1/x", status=409, codigo="conflito")
    with pytest.raises(ValueError, match="lista"):
        metadados_de_falha(metodo="POST", rota="/api/v1/x", status=409, codigo="NotFound")
    with pytest.raises(ValueError, match="template"):
        metadados_de_falha(
            metodo="POST", rota="/api/v1/x?senha=segredo", status=409, codigo="conflito"
        )


def test_campos_invalidos_sao_descartados() -> None:
    """013/R4.4, R4.5: nomes fora de `[A-Za-z0-9_.]{1,50}` (que poderiam carregar valores) somem,
    e passam no máximo 20."""
    campos = [
        "cnes",
        "distrito_id",
        "endereco.cep",
        "valor: 123",
        "x" * 51,
        "",
        *[f"c{i}" for i in range(30)],
    ]

    metadados = metadados_de_falha(
        metodo="POST",
        rota="/api/v1/unidades",
        status=422,
        codigo="validacao_dominio",
        campos=campos,
    )

    assert metadados["campos"][:3] == ["cnes", "distrito_id", "endereco.cep"]
    assert len(metadados["campos"]) == 20
    assert "valor: 123" not in metadados["campos"]


def test_codigo_vem_do_mapa_fixo() -> None:
    """013/R4.1, R4.4: cada código tem uma categoria permitida."""
    assert {codigo: categoria_de(codigo) for codigo in CODIGOS} == {
        "conflito": "conflito",
        "precondicao_falhou": "precondicao",
        "precondicao_ausente": "precondicao",
        "validacao_dominio": "validacao",
        "erro_interno": "erro_interno",
    }
