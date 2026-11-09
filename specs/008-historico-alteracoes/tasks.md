# 008 · Histórico de alterações · Tarefas

- Status: Rascunho (revisão técnica de 09/11/2026 por ViniciusVbm na consolidação final; **aguarda aprovação do Rafael**. Implementada antes da aprovação por decisão do usuário; ver `docs/RELATORIO_VALIDACAO_FINAL.md` § Desvios)
- Depende de: 001, 003, 006

- [x] T1. Índices e consulta paginada com filtros
  - Concluída em 09/11/2026 (consolidação final; `make check` verde). Prova: `tests/integration/audit/test_consulta_trilha.py`
  - Requisitos: R1.1, R1.3, R2.1
  - Pronto quando: `tests/integration/audit/test_consulta_eventos.py` passa
- [x] T2. Histórico da unidade com rótulos, nomes de referência, fuso e escopo
  - Concluída em 09/11/2026 (consolidação final; `make check` verde). Prova: `tests/integration/audit/test_consulta_trilha.py`
  - Requisitos: R1.1, R1.2, R1.4
  - Pronto quando: `tests/integration/audit/test_historico_unidade.py` passa
- [x] T3. Trilha geral com separação de eventos de acesso e mascaramento
  - Concluída em 09/11/2026 (consolidação final; `make check` verde). Prova: `tests/integration/audit/test_consulta_trilha.py`
  - Requisitos: R2.1–R2.3, R3.2
  - Pronto quando: `tests/integration/audit/test_trilha_geral.py` passa
- [x] T4. Verificação de integridade da cadeia
  - Concluída em 09/11/2026 (consolidação final; `make check` verde). Prova: `tests/integration/audit/test_consulta_trilha.py::test_verificacao_acusa_o_evento_adulterado`
  - Requisitos: R3.1
  - Pronto quando: `tests/integration/audit/test_verificar_cadeia.py` passa
- ~~T5. Particionamento mensal e comando de manutenção~~: removida (Rafael, 06/11/2026; ver design § Retenção). A R4.1 já é provada por `tests/integration/audit/test_audit_immutable.py` (001).
