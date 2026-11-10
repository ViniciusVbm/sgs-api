# CLAUDE.md

@AGENTS.md

## Específico do Claude Code
- Comandos do fluxo SDD em `.claude/commands/`: `/spec-requisitos`, `/spec-design`, `/spec-tarefas`, `/spec-implementar`, `/spec-revisar`.
- Use o modo de planejamento antes de tarefas que toquem mais de um módulo.
- Ao terminar uma tarefa, marque `[x]` em `tasks.md` somente depois de `make check` verde e diga qual teste prova a entrega.

## Agent skills

### Issue tracker

Issues no GitHub (`ViniciusVbm/sgs-api`, via `gh`), usadas como entrada de pedidos. O trabalho em si segue as specs de `specs/`. Ver `docs/agents/issue-tracker.md`.

### Triage labels

Os cinco nomes padrão: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. Ver `docs/agents/triage-labels.md`.

### Domain docs

Contexto único: `GLOSSARY.md` na raiz (ainda não existe; até lá, `steering/product.md` § Domínio) e ADRs em `docs/adr/`. Ver `docs/agents/domain.md`.
