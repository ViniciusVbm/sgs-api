# 07 · Plano de consolidação

- **Objetivo:** uma `main` única, com as melhores implementações das 15 branches, pronta para publicar num repositório GitHub novo.
- **Princípio:** consolidar **por funcionalidade**. Só duas branches têm código útil fora da `main`, e elas são incompatíveis entre si (doc 04).
- **Revisado em 09/11/2026**, depois da validação técnica (doc 03, Registro de execução).

## Estado e autorizações (09/11/2026)
| Item | Situação |
|---|---|
| Passo 0 (preservação) | **executado** em 09/11/2026 (ver abaixo) |
| Fast-forward da 011 na `main` (passo 1) | **não executado**; a `main` local e a remota continuam em `a2e2a47` |
| Push para qualquer remoto | **não autorizado** |
| Apagar branches (locais ou remotas) | **fora do plano**; nenhuma branch deve ser apagada |
| Secrets (`secrets/`) | ficam **fora do Git** (`.gitignore:21`) e fora do bundle |
| Fluxo recomendado para a `main` | **PR pela interface web do GitHub** (ADR-0008); o `gh` não está instalado nesta máquina |

## Visão geral
| Origem | Ação | Motivo |
|---|---|---|
| 11 branches incorporadas | nenhuma (já estão na `main`) | 0 commits à frente |
| `feat/011-integracao` (`556599f`) | **fast-forward integral**, por PR | 0 commits atrás, sem conflito, base escolhida; testes aprovados no `556599f` |
| `feat/003-interface-dashboard` (`8e16b17`) | **reaproveitamento de conteúdo**, sem merge nem cherry-pick | esquema incompatível e falha de autenticação |
| `feat/002-fundacao-vinicius` (`4736f81`) | nenhuma | subconjunto da 003; o conteúdo do `9245d4f` já está na `main` como `7fd3f05` (mesmo patch-id) |

## Passo 0 · Preservação (executado em 09/11/2026)
| Artefato | Local | Validação |
|---|---|---|
| Tag `arquivo/main-pre-consolidacao` (anotada) | repositório local | aponta para `a2e2a47` |
| Tag `arquivo/011-integracao` | repositório local | aponta para `556599f` |
| Tag `arquivo/003-interface-dashboard` | repositório local | aponta para `8e16b17` |
| Tag `arquivo/002-fundacao-vinicius` | repositório local | aponta para `4736f81` |
| Bundle completo (`--all`) | `~/sgs-api-backup-20261109.bundle` (com `.sha256` ao lado) | `git bundle verify` OK: histórico completo; 15 branches remotas, `main`, `docs/integration-audit` e as 4 tags |
| Cópia dos documentos originais da auditoria | `~/sgs-api-integration-audit-backup-20261109/` e `.tar.gz` | `sha256sum -c`: 11 de 11 OK. É a versão **anterior** a esta revisão |
| Secrets de dev (`jwt-keys.json`, `caddy-root.crt`) | `~/sgs-api-secrets-backup-20261109/` (diretório 700, arquivos 600) | `sha256sum -c` OK; conteúdo não exibido |

**As tags são só locais.** Elas não são enviadas ao remoto sem autorização. Para recuperar qualquer branch do bundle: `git clone ~/sgs-api-backup-20261109.bundle sgs-api-recuperado`.

## Passo 1 · Trazer a 011 para a `main` (não executado)
- **Depende de:** só do passo 0. **Não depende de nenhuma implementação I2 a I18** nem de decisões D1 a D5.
- **Conflitos previstos:** nenhum (a `main` é ancestral da 011; 63 commits à frente, 0 atrás).

### 1a. Caminho recomendado: PR pela web (ADR-0008)
1. No GitHub, abrir um PR de `feat/011-integracao` para `main`.
2. Rodar a validação local abaixo (1c) e colar o resultado do `make check` no PR. Pela exceção do ADR-0008, isso substitui o CI enquanto o GitHub Actions estiver bloqueado.
3. Merge pelo administrador, **sem squash**, para preservar os 63 commits e os trailers `Co-Authored-By`.
4. Localmente: `git fetch origin` e depois `git switch main && git merge --ff-only origin/main`.

### 1b. Caminho alternativo: fast-forward local
Só com autorização expressa. Não publica nada e não substitui o PR.
```bash
cd /home/blue5050/Projetos/sgs-api
git switch main                       # os arquivos não rastreados de docs/ acompanham sem conflito
git merge --ff-only origin/feat/011-integracao
git rev-parse --short HEAD            # espera 556599f
```
Publicar esse resultado exige `git push origin main`, que está **não autorizado** e pularia o PR do ADR-0008.

### 1c. Validação da nova `main`
```bash
uv sync --frozen                      # instala o Python 3.13 exigido (o do sistema é 3.14)
make check                            # espera 646 aprovados, 5 desmarcados
uv run pytest -m slow tests/e2e       # espera 5 aprovados; usa um projeto compose próprio
```

### 1d. Subir o ambiente (opcional, com impacto, ler antes)
```bash
mkdir -p secrets
cp ~/sgs-api-secrets-backup-20261109/jwt-keys.json secrets/
#   ou gerar uma chave nova:  uv run python -m src.tools.jwt_keys --output secrets/jwt-keys.json
docker compose -f docker/compose.yml up -d --build --wait
curl -k https://localhost/health/ready
docker compose -f docker/compose.yml exec db psql -U sgs -d sgs -Atc 'select version_num from alembic_version'   # espera 0011_08
```

**Impacto, que precisa de confirmação antes de rodar:**
- **Containers substituídos.** O nome do projeto compose é fixo (`name: sgs-api`). Hoje há containers `sgs-api-*` rodando a partir da cópia solta `/home/blue5050/Área de trabalho/sgs-api-feat-011-integracao` (conteúdo igual ao commit `fbee1da`). O `up --build` **substitui esses containers** pelos do clone em `Projetos`.
- **Volume reaproveitado.** O volume `sgs-api_db-data` é mantido. O banco está em `0011_06`, com 0 linhas em `health_units`, `audit_log` e `users`.
- **Migração na subida.** Em `APP_ENV=dev` a API aplica as migrações ao iniciar, levando o banco de `0011_06` a `0011_08`. Esse passo é só de avanço; não há perda de dados.
- **Recriar do zero:** `docker compose -f docker/compose.yml down -v` **apaga o banco** e os certificados. Só com autorização.
- **Clone errado.** Não subir o compose a partir de um clone ainda na `main` antiga (`~/sgs-api`, `~/Área de trabalho/sgs-api`): a API desse código não conhece a revisão `0011_06` do banco e não inicia.

**Comandos que não devem ser usados:**
- `uv run alembic upgrade head` no host. O serviço `db` não expõe porta e exige TLS `verify-full` com o nome `db`; as migrações rodam na subida da API em dev. Para rodá-las à mão, use o container: `docker compose -f docker/compose.yml exec api alembic upgrade head`.
- `alembic downgrade base`. É destrutivo e nenhum teste o cobre. Fica fora do roteiro.

**Resultado esperado:** `main` = `556599f`, com 003 T1 a T4, 006 T1 a T3, 011 T1 a T8, T10 e T11, e 002/T4.

## Passo 2 · Ajustes de base (bloqueado por spec)
- **Conteúdo:** achados P1, P4, P5, P6, P9 e P11 do doc 06:
  - índices `ix_equipments_unit_id` e `ix_services_equipment_id`;
  - `REVOKE DELETE` nas tabelas de exclusão lógica;
  - trigger de `updated_at`;
  - `REVOKE EXECUTE … FROM PUBLIC`;
  - preencher `Ator.papeis`;
  - `.env.example`.
- **Bloqueio:** **não há tarefa na spec 011 para isso.** Pela regra 1 do `AGENTS.md`, primeiro é preciso propor a tarefa (por exemplo, 011/T21) ou uma emenda e obter a aprovação do Rafael. Até lá, nada disso é implementado.
- **Depende de:** passo 1.

## Passo 3 · Implementação do backlog (doc 08)
A ordem segue as dependências do doc 08, e não a numeração. Resumo:
1. **Prontos assim que o passo 1 terminar** (spec aprovada, sem decisão externa): I2 (011/T12), I3 (006/T4 a T9 com 011/T16 a T18), I4 parcial (011/T13 e T15), I7 (011/T9), I10 (002/T3, T6, T8), I11 (003/T5 a T7), documentos da I14.
2. **Dependem de outra tarefa:**
   - I6 (seed) depende da I3;
   - I5 (catálogo, 011/T19) depende de I2 e de **toda** a I4, inclusive a T14;
   - I8 (011/T20) depende de 011/T1 a T19;
   - I13 depende de I3, I5 e I10.
3. **Bloqueados por decisão ou spec em Rascunho:**
   - 011/T14, parte da I4: a rota `GET /unidades/{id}/historico` é da 008/T2, e a 008 está em Rascunho;
   - por consequência, a I5 e a I8;
   - I6: D1 e spec 010;
   - I9: spec 009;
   - I12: spec 008;
   - I15: spec 004;
   - I16: spec 005;
   - módulo da I14: D5.
4. **Conteúdo reaproveitado da 003V** (sem merge):
   - o seed da I6 usa os dados de `2_SQL_Insercao_Dados.sql`;
   - a I5 reescreve as 4 consultas de `consultas_etapa3.sql`;
   - a I9 usa o formato de `/dashboard/resumo`;
   - a I3 usa o contrato das rotas de equipamento e o If-Match como referência.

Cada tarefa é feita numa branch `impl/<spec>-t<n>`, vai por PR para a `main` e só fecha com `make check` verde e `[x]` em `tasks.md`.

## Passo 4 · Front em HTML
- **Origem:** externa; o usuário tem o HTML.
- **Situação:** fica para outra etapa (decisão de 09/11). Daqui sai só o necessário para o front funcionar: CORS (`src/main.py`), o contrato `contracts/openapi.yaml`, o catálogo de consultas (I5) e o login (I10).

## Passo 5 · Publicação no repositório novo
- **Depende de:** passos 1 a 3 e decisão do grupo sobre a mudança de repositório.
- **Requer autorização:** é push.
- **Comandos:**
  ```bash
  git remote add novo <url>
  git push novo main
  git push novo 'refs/tags/arquivo/*'   # opcional
  ```
- **Histórico:** preservar o histórico, porque os trailers `Co-Authored-By` alimentam o registro de uso de IA.
- **Teste:** clonar do zero, `uv sync --frozen`, `make check`, gerar `secrets/jwt-keys.json` e `docker compose up -d --build --wait`.

## Branches depois da consolidação
**Nenhuma branch é apagada neste plano.** As 15 branches remotas continuam como estão, e as tags `arquivo/*` e o bundle garantem a recuperação. Qualquer limpeza futura exige uma decisão explícita do grupo, que não faz parte desta etapa.

## O que não entra da 003V, e por quê
| Item da 003V | Motivo |
|---|---|
| `migrations/versions/0002_etapa2_tabelas.py`, `0003_etapa3_legado.py` | revisões duplicadas; esquema incompatível |
| `src/modules/access/**` (`X-User-Id`) | falha de autenticação (P13) |
| Tabela `alteracao` e `audit/domain/alteracao.py` | duplica o `audit_log` encadeado, mais fraco (P16) |
| `src/modules/registry/**` e `dashboard/**` da 003V | dependem do esquema em português e da autenticação por cabeçalho |
| Diffs de `specs/**` e `steering/structure.md` | aprovação sem dono; contraria o AGENTS.md (P17) |
| `get-docker.sh` | sem relação com o projeto (P18) |
| `src/tools/seed_db.py` | substituído pelo `sgs-admin seed demo` (I6) |

## Critérios de aceite do passo 1
- `git rev-parse main` = `556599f…` (ou o merge do PR com esse conteúdo).
- `make check`: 646 aprovados; e2e: 5 aprovados.
- Se o passo 1d for executado: `/health/ready` em HTTPS e `alembic_version` = `0011_08`.
- As tags `arquivo/*` e o bundle continuam válidos (`git bundle verify`).
