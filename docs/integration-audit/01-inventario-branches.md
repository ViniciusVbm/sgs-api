# 01 · Inventário das branches

- Data da auditoria: 09/11/2026
- Repositório: `https://github.com/rafareloM/sgs-api` (clone local em `~/Projetos/sgs-api`)
- Branch na auditoria: `main` em `a2e2a47` (árvore limpa, sem stash, sem tags)
- Remoto: só `origin`
- Método: só leitura. Os refs locais foram conferidos contra o remoto com `git ls-remote --heads origin`; todos batiam, por isso não houve `git fetch`. Nenhuma branch foi alterada.
- Limitação: o `gh` não está instalado nesta máquina, então PRs abertos e issues não foram consultados. Os números de PR abaixo saem das mensagens de merge.

## Resumo
- **15 branches** no remoto. É o número esperado. Elas se dividem assim, sem sobreposição:

| Categoria | Quantidade | Branches |
|---|---|---|
| Branch-base | 1 | `main` |
| Já incorporadas na `main` (0 commits à frente) | 11 | as linhas 2 a 12 da tabela completa |
| Com commits fora da `main` | 3 | `feat/011-integracao`, `feat/003-interface-dashboard`, `feat/002-fundacao-vinicius` |
| **Total** | **15** | |

- As 11 incorporadas não têm conteúdo exclusivo.
- Detalhe das 3 com commits fora da `main`:

| Branch | À frente | Atrás | Último commit | Autor |
|---|---|---|---|---|
| `feat/011-integracao` | 63 | 0 | 07/11/2026, `556599f` | rafareloM |
| `feat/003-interface-dashboard` | 3 | 44 | 26/10/2026, `8e16b17` | ViniciusVbm |
| `feat/002-fundacao-vinicius` | 2 | 44 | 26/10/2026, `4736f81` | ViniciusVbm |

- A `feat/002-fundacao-vinicius` é **subconjunto** da `feat/003-interface-dashboard`: os dois commits dela (`9245d4f`, `4736f81`) são os dois primeiros da 003.
- A ponta da `feat/002-fundacao-vinicius` é **`4736f81`** (local e `git ls-remote`). O `9245d4f` é o primeiro commit da branch e pai do `4736f81`.
- O **commit** `9245d4f` ("validação entry repository test_hash") **não** é ancestral da `main`. O **conteúdo** dele, porém, está na `main`:
  - o commit `7fd3f05` (PR #12, `fix/001-auditoria-imutavel`, também de Vinicius) tem o mesmo `git patch-id --stable` (`f363919cc869`);
  - os três arquivos tocados (`src/modules/audit/domain/entry.py`, `src/modules/audit/infrastructure/repository.py`, `tests/unit/audit/test_hash.py`) são idênticos aos da `main`.
  - Verificação feita em 09/11/2026.

## Tabela completa

| # | Branch | Ponta | À frente / atrás da `main` | Incorporada? | Via | Data | Autor | Natureza |
|---|---|---|---|---|---|---|---|---|
| 1 | `main` | `a2e2a47` | — | — | — | 07/11 | Rafael Morais | base |
| 2 | `docs/003-006-aprovadas` | `84c8242` | 0 / 1 | sim | PR #20 `a2e2a47` | 07/11 | rafareloM | spec |
| 3 | `docs/011-design` | `5d82dac` | 0 / 3 | sim | PR #19 `4c373ca` | 07/11 | rafareloM | spec |
| 4 | `docs/011-requisitos` | `139c9fe` | 0 / 9 | sim | PR #18 `d2ef84a` | 07/11 | rafareloM | spec |
| 5 | `docs/adr-0008-aceito` | `39e3034` | 0 / 33 | sim | PR #10 `6a58dab` | 06/11 | rafareloM | ADR |
| 6 | `docs/adr-0008-merge-admin` | `2e79049` | 0 / 42 | sim | PR #8 `10bed74` | 06/11 | rafareloM | ADR |
| 7 | `docs/agent-skills` | `20c26df` | 0 / 41 | sim | PR #7 `2707680` | 06/11 | Rafael Morais | docs de agente |
| 8 | `docs/decisoes-06-11` | `665a34c` | 0 / 29 | sim | PR #13 `8e805aa` | 06/11 | rafareloM | spec 005 |
| 9 | `feat/001-fundacao` | `d67bb0f` | 0 / 44 | sim | PR #3 `68fd17d` | 03/10 | rafareloM | código (fundação) |
| 10 | `feat/002-t2-identity-repositories` | `f16afca` | 0 / 12 | sim | PR #16 `ec31136` | 07/11 | rafareloM | código (002/T2) |
| 11 | `fix/001-auditoria-imutavel` | `7fd3f05` | 0 / 31 | sim | PR #12 `06ce5ed` | 06/11 | ViniciusVbm | código (auditoria) |
| 12 | `fix/deps-pip-audit` | `309066b` | 0 / 41 | sim | PR #9 `c93ad99` | 06/11 | Rafael Morais | dependências |
| 13 | **`feat/011-integracao`** | `556599f` | **63 / 0** | não | — | 07/11 | rafareloM | código (003, 006, 011, 002/T4) |
| 14 | **`feat/003-interface-dashboard`** | `8e16b17` | **3 / 44** | não | — | 26/10 | ViniciusVbm | código (Etapas 2 e 3) |
| 15 | `feat/002-fundacao-vinicius` | `4736f81` | 2 / 44 | não | — | 26/10 | ViniciusVbm | subconjunto da 14 |

Outros PRs aparecem no histórico da `main` sem branch remota viva (foram apagadas depois do merge): #14 `feat/002-t1-field-cipher`, #15 `docs/002-chaves-no-settings`.

## Relação entre as branches

```
main (a2e2a47) ─────────────────────────────────────────► feat/011-integracao (+63, fast-forward)
   │
   └── d67bb0f (feat/001-fundacao, 03/10)
          └── 9245d4f ─ 4736f81 (feat/002-fundacao-vinicius)
                                  └── 8e16b17 (feat/003-interface-dashboard)
```

- A `feat/011-integracao` parte da `main` atual e tem 0 commits atrás. Pode ser aplicada por **fast-forward, sem conflito**.
- A `feat/003-interface-dashboard` parte da `main` de 03/10 (`d67bb0f`). Depois disso a `main` andou 44 commits: 002/T1, 002/T2, specs aprovadas, ADR-0008 e correção da auditoria. Tem conflito de revisão de migração e de arquivos com a `main` e com a 011 (ver doc 04).

## Commits exclusivos da `feat/011-integracao`
São 27 sem merge (os demais 36 são merges `impl/* → feat/011-integracao`), todos de 07/11/2026, por rafareloM:

| Spec/tarefa | Commits |
|---|---|
| 011/T1 carregador de `.sql` | `8666587` |
| 003/T1 matriz de papéis | `3919b40`, `cffa326` |
| 003/T2 `pode()` | `80b7ee6` |
| 003/T3 permissões efetivas | `a10ac72` |
| 003/T4 `require()`, `CurrentUser` | `822f808`, `15278ed` |
| 002/T4 TokenService ES256 e JWKS | `ad6c211` |
| 006/T1 e 011/T2 migração 0006 | `b9ec30a`, `66ca0e4`, `ce56253`, `76644b5` |
| 006/T2 domínio da unidade | `afd0f97` |
| 006/T3 criar unidade | `81456e6` |
| 011/T3 dono, índices, situação | `1101aa7` |
| 011/T4 views | `e97befc`, `7e8134c` |
| 011/T5 trigger de versão | `b7566ef` |
| 011/T6 `sp_deactivate_unit` | `17b3eb6`, `fce3643` |
| 011/T7 log do banco | `8960806`, `4cf0949` |
| 011/T8 partições e cursor | `a3ff9f5` |
| 011/T10 TLS | `bc0e7de` |
| 011/T11 anti join e full outer join | `4580b03`, `3d8c845` |
| specs | `843871c` |

## Commits exclusivos da `feat/003-interface-dashboard`
| Commit | Data | Mensagem |
|---|---|---|
| `9245d4f` | 26/10 | feat: validação entry repository test_hash (conteúdo idêntico ao de `7fd3f05`, PR #12, já na `main`) |
| `4736f81` | 26/10 | feat: integração do banco de dados e modelos (Etapa 02) |
| `8e16b17` | 26/10 | feat: implementa CRUD auditado, RBAC e dashboard via raw SQL (Etapa 03) |

## Volume de testes por branch
Contagem estática das funções `def test_*` em `tests/`. É o número de funções, não o de casos executados: com a parametrização (`@pytest.mark.parametrize`, hypothesis), as 269 funções da 011 viram 651 casos coletados. Os resultados de execução estão no doc 03, seção "Registro de execução".

| Branch | Funções de teste |
|---|---|
| `main` | 102 |
| `feat/011-integracao` | 269 (42 arquivos), contando os da `main` |
| `feat/003-interface-dashboard` | 95, sobre a base de 03/10 |
