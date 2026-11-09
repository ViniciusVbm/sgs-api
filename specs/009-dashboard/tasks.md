# 009 · Dashboard básico · Tarefas

- Status: Aprovado (Vinicius, 09/11/2026). Histórico: autoria original de rafareloM (03/10/2026); revisão técnica de ViniciusVbm (09/11/2026); implementada antes da aprovação, por decisão do usuário (`docs/RELATORIO_VALIDACAO_FINAL.md` § 9); aprovação registrada na regularização (`docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 7, item V2)
- Depende de: 006, 007, 008
- Rastreabilidade (auditoria de 09/11/2026): os arquivos de teste citados em "Pronto quando" foram consolidados em outros; o teste que prova cada tarefa é o da linha "Prova". Ver `docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 3.

- [x] T1. Consultas agregadas com escopo e filtros
  - Concluída em 09/11/2026 (consolidação final; `make check` verde). Prova: `tests/integration/dashboard/test_painel.py::test_resumo_da_rede`
  - Requisitos: R1.1–R1.6
  - Pronto quando: `tests/integration/dashboard/test_resumo.py` passa
- ~~T2. Cache com invalidação por versão~~: adiada (revisão de 09/11/2026). O resumo é medido sem cache na T3; o cache só entra se a T3 mostrar p95 acima de 1 s.
- [ ] T2b. (era T2) Cache com invalidação por versão, só se a T3 exigir
  - Requisitos: R1.7
  - Pronto quando: `tests/unit/dashboard/test_cache.py` passa
- [ ] T3. Teste de desempenho
  - Requisitos: R1.7
  - Pronto quando: `tests/e2e/test_dashboard_desempenho.py -m slow` passa

- [x] T4. Consultas estatísticas da Etapa 03 (emenda R2)
  - Concluída em 09/11/2026 (consolidação final; `make check` verde). Prova: `tests/integration/dashboard/test_painel.py::test_quatro_consultas_da_etapa_3`
  - Requisitos: R2.1–R2.5
  - Pronto quando: `tests/integration/dashboard/test_consultas_etapa3.py` passa
