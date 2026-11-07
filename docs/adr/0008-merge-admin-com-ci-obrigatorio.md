# ADR-0008: Merge pelo administrador sem aprovação, com CI obrigatório

- Status: Proposto
- Data: 2026-11-06
- Requisitos relacionados: spec 001 (R7.2); altera em parte o ADR-0006 (portão de revisão de PR)

## Contexto
- O ruleset "main protegida (spec 001, R7.2)" exigia 1 aprovação em todo PR e não tinha lista de exceções.
- O GitHub não deixa o autor aprovar o próprio PR, e o repositório tem só dois integrantes com permissão de escrita. Assim, nenhum PR do administrador (rafareloM) entrava sem a aprovação do outro integrante.
- O administrador precisa fazer merge dos próprios PRs sem depender dessa espera: o desenvolvimento do MVP fecha em 07/11/2026 e o code freeze é em 28/11/2026.
- Pôr o administrador na lista de exceções do ruleset existente resolveria, mas a exceção vale para o ruleset inteiro: ele também poderia fazer merge com o CI vermelho, contrariando a 001/R7.2.
- Em 06/11/2026 o GitHub Actions parou de rodar os jobs ("account is locked due to a billing issue"). Sem CI, os checks obrigatórios nunca passam e nenhum PR entra na `main`.

## Decisão
A proteção da `main` passa a ser feita por dois rulesets:

| Ruleset | Regras | Exceções |
|---|---|---|
| main protegida (spec 001, R7.2) | só por PR (0 aprovações); checks `quality` e `compose-smoke` verdes com a branch atualizada; sem force-push nem exclusão | administrador, só ao fazer merge de PR, **provisoriamente** (ver abaixo) |
| revisão humana (ADR-0008) | 1 aprovação, descartada quando chegam commits novos | administrador do repositório, só ao fazer merge de PR |

- O administrador pode fazer merge sem aprovação (`gh pr merge <n> --admin` ou "bypass rules" na interface), nunca por push direto.
- Antes de um merge sem aprovação, o PR passa por revisão de agente (`/spec-revisar` quando houver spec aprovada) e o resultado fica registrado no PR.
- PRs dos demais integrantes continuam precisando de 1 aprovação e do CI verde.

### Exceção provisória: CI indisponível
Enquanto o GitHub Actions estiver bloqueado, o administrador também pode fazer merge sem os checks `quality` e `compose-smoke`, desde que:
- o `make check` tenha passado localmente na branch do PR, atualizada com a `main`, e o resultado esteja registrado no PR; PRs só de documentação dispensam o `make check`;
- o merge não aconteça com falha conhecida em nenhuma etapa da esteira.

A exceção sai do ruleset "main protegida" assim que o CI voltar a rodar ou a nova esteira entrar no lugar. Essa troca de esteira pede um ADR próprio.

## Consequências
- Os PRs do administrador deixam de ter um segundo par de olhos humano. A barreira passa a ser o CI mais a revisão por agente.
- Durante a exceção, a 001/R7.2 deixa de ser garantida pelo GitHub para o administrador e passa a depender do `make check` local (que exige o Docker) e dos hooks de pre-commit.
- A rastreabilidade por integrante (ADR-0006) não muda: commits e PRs continuam citando spec e tarefa.
- `AGENTS.md`, `steering/sdd-workflow.md` e o `README.md` passam a descrever as duas regras.

## Alternativas consideradas
- Exceção permanente para o administrador no ruleset do CI: mais simples, mas libera merge com CI vermelho mesmo com o Actions funcionando.
- Tirar os checks obrigatórios do ruleset: qualquer integrante faria merge sem CI.
- Zerar as aprovações para todos: o PR de qualquer integrante entraria sem revisão.
- Manter como estava: cada PR do administrador espera a aprovação do outro integrante, e, com o Actions bloqueado, nenhum PR entra.
