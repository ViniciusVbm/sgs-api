# Labels de triagem

As skills falam em cinco papéis canônicos de triagem. Este arquivo liga esses papéis às labels usadas no GitHub Issues deste repo.

| Label em mattpocock/skills | Label no nosso tracker | Significado                                         |
| -------------------------- | ---------------------- | --------------------------------------------------- |
| `needs-triage`             | `needs-triage`         | Um integrante precisa avaliar a issue               |
| `needs-info`               | `needs-info`           | Aguardando mais informação de quem abriu            |
| `ready-for-agent`          | `ready-for-agent`      | Especificada o bastante para um agente sem supervisão |
| `ready-for-human`          | `ready-for-human`      | Precisa de implementação humana                     |
| `wontfix`                  | `wontfix`              | Não será feita                                      |

Quando uma skill mencionar um papel (ex.: "apply the AFK-ready triage label"), use a label correspondente desta tabela.

**Neste repo, `ready-for-agent` não autoriza código.** Significa que a issue está clara o bastante para um agente redigir ou alterar a spec (`/spec-requisitos`). A implementação só começa por uma tarefa de spec aprovada (ver `docs/agents/issue-tracker.md` § Relação com o fluxo SDD).

Edite a coluna "Label no nosso tracker" se o vocabulário mudar.
