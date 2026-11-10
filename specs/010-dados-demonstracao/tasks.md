# 010 · Dados de demonstração · Tarefas

- Status: Aprovado (Vinicius, 09/11/2026). Histórico: autoria original de rafareloM (03/10/2026); revisão técnica de ViniciusVbm (09/11/2026); implementada antes da aprovação, por decisão do usuário (`docs/RELATORIO_VALIDACAO_FINAL.md` § 9); aprovação registrada na regularização (`docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 7, item V3)
- Depende de: 006, 007
- Rastreabilidade (auditoria de 09/11/2026): os arquivos de teste citados em "Pronto quando" foram consolidados em outros; o teste que prova cada tarefa é o da linha "Prova". Ver `docs/relatorios/REGULARIZACAO_GOVERNANCA_SPECS.md` § 3.

- [x] T1. Arquivos YAML de demonstração (Saúde Mental + casos especiais + pendências)
  - Concluída em 09/11/2026 (consolidação final; `make check` verde). Prova: `tests/integration/tools/test_seed_demo.py (JSON validado pela carga)`
  - Requisitos: R1.2, R1.3, R1.5
  - Pronto quando: `tests/unit/seeds/test_yaml_valido.py` passa
- [x] T2. Comando `sgs-admin seed demo` idempotente com usuários por papel
  - Concluída em 09/11/2026 (consolidação final; `make check` verde). Prova: `tests/integration/tools/test_seed_demo.py`
  - Requisitos: R1.1, R1.4, R1.6
  - Pronto quando: `tests/integration/seeds/test_seed_demo.py` passa
- [ ] T3. Conversor da planilha de rede com relatório de rejeitos
  - Requisitos: R2.1, R2.2
  - Pronto quando: `tests/unit/seeds/test_classificador_planilha.py` passa
