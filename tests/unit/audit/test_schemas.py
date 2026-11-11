"""Schemas da trilha sem dados de origem fora do detalhe (spec 013, T12; R8.6)."""

from src.modules.audit.api.schemas import EventoDetalheOut, EventoOut

ORIGEM = {"ip", "user_agent", "sessao_id", "session_id", "request_id"}


def test_evento_out_nao_tem_campos_de_origem() -> None:
    """013/R8.6: a lista e o histórico usam `EventoOut`, que não tem IP, User-Agent, sessão nem
    request id; só o detalhe os tem."""
    assert ORIGEM.isdisjoint(EventoOut.model_fields)
    assert {"ip", "user_agent", "sessao_id", "origem_restrita"} <= set(
        EventoDetalheOut.model_fields
    )
