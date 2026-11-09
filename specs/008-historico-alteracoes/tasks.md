# 008 · Histórico de alterações · Tarefas

- Status: Aprovado (Vinicius, 09/11/2026). Histórico: autoria original de rafareloM (03/10/2026); revisão técnica de ViniciusVbm (09/11/2026); implementada antes da aprovação, por decisão do usuário (`docs/RELATORIO_VALIDACAO_FINAL.md` § 9); aprovação registrada na regularização (`docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 7, item V1)
- Depende de: 001, 003, 006
- Rastreabilidade (auditoria de 09/11/2026): os arquivos de teste citados em "Pronto quando" foram consolidados em outros; o teste que prova cada tarefa é o da linha "Prova". Ver `docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 3.

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
- [ ] T6. Testes dos filtros de período e autor (melhoria funcional; D008-5; não bloqueia a aprovação)
  - Requisitos: R1.3, R2.1
  - Pronto quando: `tests/integration/audit/test_consulta_trilha.py` tem testes dos filtros `de`, `ate` e `autor` no histórico da unidade e `de`, `ate`, `entidade_tipo`, `entidade_id` e `autor` na trilha geral
