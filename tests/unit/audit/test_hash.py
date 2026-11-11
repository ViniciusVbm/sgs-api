"""Hash encadeado dos registros de auditoria (spec 001, R5.3)."""

import hashlib
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.errors import DomainValidationError
from src.modules.audit.domain.entry import GENESIS_HASH, Ator, AuditEntry, Entidade, Mudanca
from src.modules.audit.infrastructure.repository import SqlAuditStore

QUANDO = datetime(2026, 10, 3, 12, 0, 0, 123456, tzinfo=UTC)
USUARIO = UUID("01928a3b-0000-7000-8000-000000000001")


def _registro(**alteracoes: Any) -> AuditEntry:
    campos: dict[str, Any] = {
        "prev_hash": GENESIS_HASH,
        "occurred_at": QUANDO,
        "action": "unidade.atualizada",
        "actor": Ator(user_id=USUARIO, papeis=("GESTOR_DADOS",), ip="10.0.0.1", request_id="r1"),
        "entity": Entidade(tipo="unidade", id="42"),
        "changes": (Mudanca(campo="telefone", de="8133330000", para="8133331111"),),
        "metadata": {"motivo": "atualização"},
    }
    return AuditEntry.create(**(campos | alteracoes))


def test_hash_e_sha256_do_hash_anterior_mais_o_conteudo_canonico() -> None:
    """001/R5.3"""
    canonico = (
        '{"action":"unidade.atualizada","actor_roles":["GESTOR_DADOS"],'
        '"actor_user_id":"01928a3b-0000-7000-8000-000000000001",'
        '"changes":[{"campo":"telefone","de":"8133330000","para":"8133331111"}],'
        '"entity_id":"42","entity_type":"unidade","ip":"10.0.0.1",'
        '"metadata":{"motivo":"atualização"},"occurred_at":"2026-10-03T12:00:00.123456+00:00",'
        '"request_id":"r1","session_id":null}'
    )

    registro = _registro()

    assert registro.canonical_content() == canonico.encode()
    assert registro.hash == hashlib.sha256((GENESIS_HASH + canonico).encode()).hexdigest()
    assert registro.recompute_hash() == registro.hash


def test_registro_isola_estruturas_json_mutaveis() -> None:
    metadata = {"detalhes": {"marcadores": ["original"]}}
    valor_anterior = {"itens": [1]}
    mudanca = Mudanca(campo="dados", de=valor_anterior, para=None)
    registro = _registro(metadata=metadata, changes=(mudanca,))
    conteudo_original = registro.canonical_content()

    metadata["detalhes"]["marcadores"].append("alterado")
    valor_anterior["itens"].append(2)

    assert registro.canonical_content() == conteudo_original
    assert registro.recompute_hash() == registro.hash
    with pytest.raises(TypeError):
        registro.metadata["detalhes"]["novo"] = True
    with pytest.raises(AttributeError):
        registro.metadata["detalhes"]["marcadores"].append("alterado")


VALORES_JSON = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=20),
    lambda filhos: st.lists(filhos, max_size=3) | st.dictionaries(st.text(max_size=8), filhos),
    max_leaves=8,
)


@given(st.dictionaries(st.text(max_size=8), VALORES_JSON, min_size=2))
def test_hash_nao_depende_da_ordem_das_chaves(metadados: dict[str, Any]) -> None:
    """001/R5.3"""
    invertido = dict(reversed(list(metadados.items())))

    assert _registro(metadata=metadados).hash == _registro(metadata=invertido).hash


ALTERACOES: dict[str, dict[str, Any]] = {
    "prev_hash": {"prev_hash": "f" * 64},
    "occurred_at": {"occurred_at": QUANDO + timedelta(microseconds=1)},
    "action": {"action": "unidade.criada"},
    "actor": {"actor": Ator(user_id=USUARIO, papeis=("AUDITOR",), ip="10.0.0.1")},
    "entity": {"entity": Entidade(tipo="unidade", id="43")},
    "changes": {"changes": (Mudanca(campo="telefone", de="8133330000", para="0"),)},
    "metadata": {"metadata": {"motivo": "outro"}},
}


@pytest.mark.parametrize("alteracao", ALTERACOES.values(), ids=ALTERACOES.keys())
def test_qualquer_campo_alterado_muda_o_hash(alteracao: dict[str, Any]) -> None:
    """001/R5.3"""
    assert _registro(**alteracao).hash != _registro().hash


def test_registro_adulterado_nao_confere_com_o_hash() -> None:
    """001/R5.3"""
    adulterado = replace(_registro(), action="unidade.removida")

    assert adulterado.recompute_hash() != adulterado.hash


async def test_repositorio_recusa_hash_inconsistente() -> None:
    adulterado = replace(_registro(), metadata={"motivo": "alterado depois do hash"})
    sessao = AsyncMock()

    with pytest.raises(ValueError, match="hash"):
        await SqlAuditStore(cast(AsyncSession, sessao)).append(adulterado)

    sessao.execute.assert_not_awaited()


def test_mesmo_instante_em_outro_fuso_gera_o_mesmo_hash() -> None:
    """001/R5.3 (datas sempre em UTC no conteúdo canônico)"""
    recife = timezone(timedelta(hours=-3))

    assert _registro(occurred_at=QUANDO.astimezone(recife)).hash == _registro().hash


@pytest.mark.parametrize(
    "invalido",
    [
        {"occurred_at": datetime(2026, 10, 3, 12, 0)},  # noqa: DTZ001 - sem fuso de propósito
        {"action": "UnidadeAtualizada"},
        {"prev_hash": "abc"},
        {"metadata": {"valor": float("nan")}},
    ],
)
def test_registro_invalido_e_recusado(invalido: dict[str, Any]) -> None:
    """001/R5.3"""
    with pytest.raises(DomainValidationError):
        _registro(**invalido)


def test_ip_do_ator_e_validado_e_normalizado() -> None:
    """001/R5.3 (o IP entra no hash; a forma normalizada evita dois textos para o mesmo IP)"""
    with pytest.raises(DomainValidationError):
        Ator(ip="999.1.1.1")
    assert Ator(ip="2001:DB8:0:0:0:0:0:1").ip == "2001:db8::1"


# --- Spec 013, T1: campos novos e emenda à canonicalização da 001 (013 design § Emenda à spec 001)

# Registro "v1" (anterior à 013) e o hash que o código de `main` @ 4efd36c calculava para ele,
# capturado antes de qualquer mudança da T1. Se este teste quebrar, todo o histórico quebrou.
HASH_V1 = "c5c274090b522020041a0fb6fae42fe969c880a7d10a014d37c212fdc670754f"


def _registro_v1(**alteracoes: Any) -> AuditEntry:
    campos: dict[str, Any] = {
        "prev_hash": GENESIS_HASH,
        "occurred_at": datetime(2026, 11, 11, 12, 30, 45, 123456, tzinfo=UTC),
        "action": "unidade.atualizada",
        "actor": Ator(
            user_id=UUID("11111111-1111-1111-1111-111111111111"),
            papeis=("GESTOR_DADOS",),
            session_id=UUID("22222222-2222-2222-2222-222222222222"),
            ip="10.0.0.7",
            request_id="req-1",
        ),
        "entity": Entidade(tipo="unidade", id="33333333-3333-3333-3333-333333333333"),
        "changes": (Mudanca(campo="phone", de="8130000000", para="8131111111"),),
        "metadata": {"motivo": "teste"},
    }
    return AuditEntry.create(**(campos | alteracoes))


def test_hash_de_registro_v1_nao_muda() -> None:
    """013/R1.5: sem os campos novos, o conteúdo canônico e o hash são os de antes da 013."""
    registro = _registro_v1()

    assert registro.hash == HASH_V1
    for chave in ("actor_type", "origin", "user_agent", "result", "result_reason"):
        assert f'"{chave}"'.encode() not in registro.canonical_content()


CAMPOS_NOVOS: dict[str, tuple[dict[str, Any], str]] = {
    "actor_type": ({"actor": Ator(user_id=USUARIO, tipo="usuario")}, '"actor_type":"usuario"'),
    "origin": ({"actor": Ator(user_id=USUARIO, origem="api")}, '"origin":"api"'),
    "user_agent": (
        {"actor": Ator(user_id=USUARIO, user_agent="Mozilla/5.0")},
        '"user_agent":"Mozilla/5.0"',
    ),
    "result": ({"result": "success"}, '"result":"success"'),
    "result_reason": (
        {"result": "failure", "result_reason": "conflito"},
        '"result_reason":"conflito"',
    ),
}


@pytest.mark.parametrize("campo", CAMPOS_NOVOS.keys())
def test_campo_novo_entra_no_hash(campo: str) -> None:
    """013/R1.1, R4.1, R5.2: preenchido, o campo entra no conteúdo canônico e muda o hash;
    anulado depois (adulteração), o hash gravado deixa de conferir."""
    alteracao, trecho = CAMPOS_NOVOS[campo]
    base = _registro(actor=Ator(user_id=USUARIO))
    com_campo = _registro(**alteracao)

    assert trecho.encode() in com_campo.canonical_content()
    assert com_campo.hash != base.hash
    if campo in {"result", "result_reason"}:
        anulado = replace(com_campo, result=None, result_reason=None)
    else:
        anulado = replace(com_campo, actor=Ator(user_id=USUARIO))
    assert anulado.recompute_hash() != com_campo.hash


def test_usuario_sem_id_e_rejeitado() -> None:
    """013/R1.1, R1.2: tipo `usuario` exige `actor_user_id`; tipo fora do domínio é recusado;
    os automáticos não ganham usuário."""
    with pytest.raises(DomainValidationError):
        Ator(tipo="usuario")
    with pytest.raises(DomainValidationError):
        Ator(tipo="robo")
    assert Ator(tipo="seed", origem="sgs-admin seed demo").user_id is None


@pytest.mark.parametrize(
    "invalido",
    [
        {"result": "talvez"},
        {"result": "failure"},  # falha sem categoria
        {"result": "success", "result_reason": "conflito"},  # sucesso não tem categoria
        {"result": "denied", "result_reason": "outra"},
    ],
    ids=["resultado", "falha_sem_categoria", "sucesso_com_categoria", "categoria"],
)
def test_valores_novos_fora_do_dominio_sao_recusados(invalido: dict[str, Any]) -> None:
    """013/R1.1, R4.1 (os mesmos domínios dos CHECKs da migração 0013_01)"""
    with pytest.raises(DomainValidationError):
        _registro(**invalido)
