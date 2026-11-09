# 009 · Dashboard básico · Tarefas

- Status: Rascunho (revisão técnica de 09/11/2026 por ViniciusVbm na consolidação final; **aguarda aprovação do Rafael**. Implementada antes da aprovação por decisão do usuário; ver `docs/RELATORIO_VALIDACAO_FINAL.md` § Desvios)
- Depende de: 006, 007, 008

- [ ] T1. Consultas agregadas com escopo e filtros
  - Requisitos: R1.1–R1.6
  - Pronto quando: `tests/integration/dashboard/test_resumo.py` passa
- ~~T2. Cache com invalidação por versão~~: adiada (revisão de 09/11/2026). O resumo é medido sem cache na T3; o cache só entra se a T3 mostrar p95 acima de 1 s.
- [ ] T2b. (era T2) Cache com invalidação por versão, só se a T3 exigir
  - Requisitos: R1.7
  - Pronto quando: `tests/unit/dashboard/test_cache.py` passa
- [ ] T3. Teste de desempenho
  - Requisitos: R1.7
  - Pronto quando: `tests/e2e/test_dashboard_desempenho.py -m slow` passa

- [ ] T4. Consultas estatísticas da Etapa 03 (emenda R2)
  - Requisitos: R2.1–R2.5
  - Pronto quando: `tests/integration/dashboard/test_consultas_etapa3.py` passa
