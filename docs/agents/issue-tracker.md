# Issue tracker: GitHub

As issues deste repo ficam no GitHub Issues de `ViniciusVbm/sgs-api` (repositório oficial desde a publicação de 09/11/2026). Use o `gh` CLI para todas as operações. Títulos, corpos e comentários em português.

## Relação com o fluxo SDD

A fonte da verdade do trabalho são as specs em `specs/NNN-*/` (ver `steering/sdd-workflow.md`). Uma issue é **entrada**: bug, ideia, dúvida ou pedido do cliente. Ela não autoriza código.

- Nada é implementado a partir de uma issue sem antes virar requisito, design e tarefa numa spec com os três arquivos em `Status: Aprovado` (regra 1 do `AGENTS.md`). O caminho é `/spec-requisitos`, depois `/spec-design` e `/spec-tarefas`.
- Ao ligar uma issue a uma spec, comente na issue o caminho da spec e os IDs afetados (`R1.2`, `T3`). Na spec, cite a issue (`#12`).
- Commits e PRs continuam citando spec e tarefa (`feat(identity): login LDAP (004/T5)`). Use `Closes #12` no PR só quando ele resolve a issue inteira.
- O agente nunca marca uma spec como `Aprovado`.

## Convenções

- **Criar uma issue**: `gh issue create --title "..." --body "..."`. Para corpo com várias linhas, use heredoc.
- **Ler uma issue**: `gh issue view <número> --json number,title,body,labels,comments`.
- **Listar issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`, com os filtros `--label` e `--state` adequados.
- **Tornar uma issue sub-issue de outra**: `gh issue create --parent <pai> ...`, ou `gh issue edit <pai> --add-sub-issue <filha>` depois (`gh` 2.94+). Com `gh` mais antigo: `gh api --method POST repos/<owner>/<repo>/issues/<pai>/sub_issues -F sub_issue_id=<id-de-banco-da-filha>` (id de banco, como em **Bloqueio** abaixo). Sem sub-issues, ponha `Part of #<pai>` no topo do corpo da filha.
- **Comentar**: `gh issue comment <número> --body "..."`
- **Aplicar / remover labels**: `gh issue edit <número> --add-label "..."` / `--remove-label "..."`
- **Fechar**: `gh issue close <número> --comment "..."`

O `gh` descobre o repo pelo `git remote -v` quando roda dentro do clone.

## Pull requests como superfície de triagem

**PRs as a request surface: no.** _(Mude para `yes` se o repo passar a tratar PRs externos como pedidos de funcionalidade; o `/triage` lê esta flag.)_

Com `yes`, PRs passam pelas mesmas labels e estados das issues, usando os equivalentes `gh pr`:

- **Ler um PR**: `gh pr view <número> --comments` e `gh pr diff <número>` para o diff.
- **Listar PRs externos para triagem**: `gh api --paginate 'repos/{owner}/{repo}/pulls?state=open' --jq '.[] | select(.author_association | IN("OWNER","MEMBER","COLLABORATOR") | not) | {number, title, author: .user.login, author_association, labels: [.labels[].name]}'`.
- **Comentar / rotular / fechar**: `gh pr comment`, `gh pr edit --add-label`/`--remove-label`, `gh pr close`.

O GitHub usa uma única numeração para issues e PRs, então um `#42` solto pode ser qualquer um dos dois: tente `gh pr view 42` e, se falhar, `gh issue view 42`.

## Quando uma skill disser "publish to the issue tracker"

Crie uma issue no GitHub.

## Quando uma skill disser "fetch the relevant ticket"

Leia como em **Ler uma issue** acima.

## Operações de wayfinding

Usadas pelo `/wayfinder`. O **mapa** é uma única issue, com issues **filhas** como tickets.

- **Mapa**: uma issue com a label `wayfinder:map`, cujo corpo tem Notes / Decisions-so-far / Fog. `gh issue create --label wayfinder:map`.
- **Ticket filho**: uma issue ligada ao mapa como sub-issue do GitHub (ver **Tornar uma issue sub-issue de outra**). Onde não houver sub-issues, adicione a filha a uma task list no corpo do mapa e ponha `Part of #<mapa>` no topo do corpo da filha. Labels: `wayfinder:<tipo>` (`research`/`prototype`/`grilling`/`task`). Ao ser assumido, o ticket é atribuído a quem está conduzindo.
- **Bloqueio**: as **dependências nativas de issue** do GitHub, que são a representação canônica e visível na interface. Adicione uma aresta com `gh api --method POST repos/<owner>/<repo>/issues/<filha>/dependencies/blocked_by -F issue_id=<id-de-banco-do-bloqueador>`, onde `<id-de-banco-do-bloqueador>` é o **id de banco** numérico (`gh api repos/<owner>/<repo>/issues/<n> --jq .id`, _não_ o `#número` nem o `node_id`). O GitHub informa `issue_dependencies_summary.blocked_by` (só bloqueadores abertos, que é o que vale). Onde não houver dependências, use uma linha `Blocked by: #<n>, #<n>` no topo do corpo da filha. Um ticket está desbloqueado quando todos os bloqueadores estão fechados.
- **Consulta da fronteira**: liste as filhas abertas do mapa (`gh issue list --state open`, restrito às sub-issues / task list do mapa), descarte as que têm bloqueador aberto (`issue_dependencies_summary.blocked_by > 0`, ou issue aberta na linha `Blocked by`) ou responsável atribuído; vence a primeira na ordem do mapa.
- **Assumir**: `gh issue edit <n> --add-assignee @me`, como primeira escrita da sessão.
- **Resolver**: `gh issue comment <n> --body "<resposta>"`, depois `gh issue close <n>`, depois acrescente um ponteiro de contexto (resumo + link) em Decisions-so-far no mapa.
