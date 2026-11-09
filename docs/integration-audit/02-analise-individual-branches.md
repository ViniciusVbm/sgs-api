# 02 · Análise individual das branches

Cada branch foi comparada com a `main` (`a2e2a47`) por `git diff main...<branch>` e lida arquivo por arquivo com `git show <branch>:<path>`.

Nenhuma branch tem frontend: nenhum arquivo `.html`, `.js`, `.ts`, `.tsx`, `.vue`, `.css` ou de template. O front em HTML existe fora do repositório e será integrado depois, por decisão do usuário em 09/11/2026.

**Classificação das 15 branches:** 1 branch-base (`main`, seção 0), 11 já incorporadas (seção A) e 3 com commits fora da `main` (seções B, C e D). São 1 + 11 + 3 = 15.

---

## 0. `main` (branch-base, `a2e2a47`, 07/11/2026)

**Papel:** é a referência de comparação de todas as outras e o destino da consolidação.

**Conteúdo:**
- spec 001 completa (9 de 9 tarefas);
- spec 002 T1 (`FieldCipher`) e T2 (tabelas e repositórios de identidade);
- módulos `audit` e `identity`, sem rotas de negócio;
- só `/health/live` e `/health/ready`;
- migrações `0001`, `0001_1` e `0002`.

**Testes:** 102 funções de teste. Não foram executadas na `main` isoladamente nesta auditoria: estão todas contidas na 011, onde foram executadas (doc 03, Registro de execução).

**Limitação:** não tem login nem módulos de cadastro, acesso ou dashboard. Esses vêm da 011.

---

## A. Branches já incorporadas na `main` (sem conteúdo exclusivo)

Estas 11 branches têm **0 commits à frente** da `main`. Tudo o que fizeram já está lá, e nenhuma precisa de ação na consolidação. Depois da consolidação, podem ser apagadas, com autorização.

| Branch | PR | Objetivo | Arquivos (no merge) | Código? | Testes |
|---|---|---|---|---|---|
| `feat/001-fundacao` | #3 | Spec 001: esqueleto FastAPI, config, erros problem+json, logs com redação, auditoria com cadeia de hash, migração 0001, CI, compose | 79 arquivos, +4.560: `src/core/*`, `src/modules/audit/*`, `migrations/versions/0001_base.py`, `docker/*`, `.github/workflows/ci.yml` | sim | health, headers, migrações, hash, config, erros, redação |
| `feat/002-t2-identity-repositories` | #16 | 002/T2: tabelas `users`, `sessions`, `refresh_tokens` e repositórios | 27 arquivos, +1.243: `migrations/versions/0002_identity.py`, `src/modules/identity/*` | sim | `tests/integration/identity/test_repositories.py`, `tests/unit/identity/*` |
| `fix/001-auditoria-imutavel` | #12 | Congela o JSON do registro de auditoria e confere o hash antes de gravar (001/R5.3) | `audit/domain/entry.py`, `audit/infrastructure/repository.py`, `tests/unit/audit/test_hash.py` | sim | 2 testes novos em `test_hash.py` |
| `fix/deps-pip-audit` | #9 | Atualiza dependências apontadas pelo pip-audit | `uv.lock` | não | — |
| `docs/agent-skills` | #7 | Instruções de agentes: issue tracker, labels, domínio | `CLAUDE.md`, `docs/agents/*` | não | — |
| `docs/adr-0008-merge-admin` | #8 | ADR-0008: merge pelo admin com CI | `docs/adr/0008-*`, `AGENTS.md`, `README.md` | não | — |
| `docs/adr-0008-aceito` | #10 | Marca o ADR-0008 como aceito | `docs/adr/*` | não | — |
| `docs/decisoes-06-11` | #13 | ADR-0009 (SQL explícito), assinatura dos relatórios (005/R5) | `docs/adr/0009-*`, specs 002, 005, 006, 009 | não | — |
| `docs/011-requisitos` | #18 | Requisitos da 011 e emendas da 006 e da 008 | `specs/011/requirements.md` (+133), specs 006 e 008 | não | — |
| `docs/011-design` | #19 | Design e tarefas da 011; tarefas da 003 e da 006 | `specs/011/design.md` (+226), `specs/011/tasks.md` (+140), `steering/sdd-workflow.md` (exceção provisória de aprovação) | não | — |
| `docs/003-006-aprovadas` | #20 | Aprova requisitos e design da 003 e da 006 | 5 arquivos de spec | não | — |

Em termos de requisitos, essas branches entregam a **fundação**:
- auditoria imutável com cadeia de hash (Segurança/Auditoria);
- tabelas de identidade (IAM, parcial);
- testes unitários e de integração;
- CI;
- a documentação de specs e ADRs.

O status de cada requisito está na matriz (doc 03).

---

## B. `feat/011-integracao` (rafareloM, 63 commits, 07/11/2026)

**Objetivo aparente:** branch de integração das tarefas implementadas das specs 003 (RBAC), 006 (cadastro), 011 (recursos de banco de dados) e 002/T4 (tokens). Cada tarefa foi feita numa branch `impl/*` e incorporada aqui. Ela parte da `main` atual, com 0 commits atrás.

**Histórico:** 27 commits de trabalho e 36 de merge. A lista por tarefa está no doc 01.

### Arquivos
São 188 arquivos e cerca de 11,9 mil linhas. Nenhum arquivo foi removido.

**Criados:**
- `migrations/sql/**`: 66 arquivos `.sql`, um por objeto de banco (R11).
- `migrations/sql_loader.py`.
- `migrations/versions/0003_access.py`, `0003_1_authz_version.py`, `0006_registry.py` e `0011_03` a `0011_08`.
- `src/core/escopo.py`, `paginacao.py` e `sql.py`.
- `src/modules/access/**`, `src/modules/registry/**`, `src/modules/dashboard/**`.
- `src/modules/identity/{api,application,domain/tokens.py,infrastructure/tokens.py}`.
- `src/tools/jwt_keys.py`, `src/tools/sgs_admin.py`.
- `docker/postgres/gerar-certificados.sh`, `pg_hba.conf`.
- Cerca de 40 arquivos de teste.

**Modificados:**
- `src/core/{config,db,errors,problem}.py` e `src/main.py`.
- `docker/compose.yml`, `.env.example`, `.github/workflows/ci.yml`.
- `contracts/openapi.yaml`, `pyproject.toml`, `uv.lock`.
- `docs/architecture/modelo-dados.md`.
- Specs 002, 003, 006 e 011.

### Banco de dados
**Tabelas:**
- `districts`, `technical_areas`, `unit_types`, `equipment_types`, `service_types`: referências com seed de domínio fechado (8, 4, 7, 3 e 4 linhas).
- `health_units`, `equipments`, `services`.
- `roles` (7), `permissions` (17), `role_permissions` (51).
- `role_assignments`, `group_role_mappings`.
- `db_change_log`, particionada por mês.
- `users` ganha a coluna `authz_version`.

**Integridade:**
- ON UPDATE CASCADE em `fk_equipments_equipment_type_code_equipment_types` (`migrations/sql/0006/16_equipments.sql:25`).
- ON DELETE SET NULL em `services.equipment_id` (`0006/17_services.sql:28`).
- ON DELETE RESTRICT em `equipments.unit_id` e `services.unit_id`.
- CHECK de status e de `pending_issues` (não negativo).
- DEFAULT em `version`, `quantity` e `in_cnes`.
- UNIQUE parcial de CNES, UNIQUE de (distrito, nome normalizado).
- Coluna gerada `name_normalized`.

**Objetos:**

| Tipo | Objetos |
|---|---|
| Views | `vw_unit_inventory` (3 JOINs internos e 2 LEFT JOINs com agregados), `vw_unit_history` (4 JOINs); ambas `security_invoker` |
| Funções | `fn_normalize_name` (SQL, IMMUTABLE); `fn_registration_status` (plpgsql com IF/ELSIF) |
| Procedures | `sp_deactivate_unit` (UPDATE com `FOR UPDATE`, SQLSTATE `SGS01`); `sp_ensure_monthly_partitions` (CURSOR `c_meses` explícito, SECURITY DEFINER) |
| Triggers | `trg_health_units_version` (BEFORE UPDATE); `trg_registry_change_log` (AFTER I/U/D em 3 tabelas, grava `db_change_log`); `trg_roles_protect_system` |
| Índices | `ix_health_units_cnes`, `ix_health_units_district_id_name_normalized`, `ix_health_units_name_normalized_trgm` (GIN), `ix_audit_log_entity`, `ix_services_unit_id`, `ix_db_change_log_occurred_at`, `ix_role_assignments_user_id` |
| Papéis | `sgs_owner` (NOLOGIN, dono dos objetos SECURITY DEFINER); privilégios mínimos de `sgs_app` |

**Cadeia do Alembic:** 0001 → 0001_1 → 0002 → 0003 → 0003_1 → 0006 → 0011_05 → 0011_03 → 0011_06 → 0011_04 → 0011_07 → 0011_08. A ordem não é numérica; os commits `chore(migrations)` explicam por quê.

### Backend
São 6 rotas:

| Rota | Proteção |
|---|---|
| `/health/live`, `/health/ready` | pública |
| `/.well-known/jwks.json` | pública |
| `POST /api/v1/unidades` | `require("unidade:create")` |
| `GET /api/v1/dashboard/consultas/unidades-sem-servico` | `dashboard:read` |
| `GET /api/v1/dashboard/consultas/conciliacao-unidade-equipamento` | `dashboard:read` |

- Todo o SQL de negócio é explícito: arquivos `.sql` carregados por `src/core/sql.py` (ADR-0009).
- Filtros de `distrito`, `tipo` e paginação.
- **Frontend:** nenhum.

### Segurança e autenticação
- `CurrentUser` valida o Bearer ES256 e confere a sessão e o usuário a cada requisição (`identity/api/deps.py`).
- JWKS com rotação por `kid`.
- `require()` nega por padrão; o 403 é auditado como `acesso.negado`.
- Escopos Global, Área, Distrito e Unidade.
- TLS `verify-full` entre a API e o PostgreSQL no compose.
- **Não há rota de login** (002/T3 aberta), nem LDAP, nem OIDC.

### Testes
São 269 funções contando as da `main`, que geram 651 casos coletados por causa da parametrização.

**Executados na validação de 09/11/2026, no commit `556599f`:** `make check` aprovou 646 casos (5 `slow` ficaram de fora); os 5 e2e de TLS foram rodados à parte e aprovados. O detalhe está no doc 03, Registro de execução.

Arquivos de teste:
- `tests/integration/access/*` (seed da matriz, permissões efetivas, `require` 401/403/404, integridade);
- `tests/integration/registry/*` (criar unidade: 14 casos com concorrência; integridade CASCADE/SET NULL/RESTRICT; normalização; situação cadastral; procedure; trigger de versão);
- `tests/integration/audit/test_log_banco*.py`, `test_particoes.py`;
- `tests/integration/db/test_views.py`, `test_privilegios.py`;
- `tests/integration/dashboard/test_consultas_qualidade.py` (15);
- `tests/integration/tools/test_sgs_admin_particoes.py`;
- `tests/e2e/test_tls_banco.py` (marcado `slow`);
- unitários de tokens, escopo, matriz, domínio da unidade e carregador de SQL.

Os testes de integração usam testcontainers e precisam de Docker.

### Problemas identificados
O detalhe está no doc 06:
- `actor_roles` sempre vazio;
- `manager_name` sem máscara no `audit_log`;
- a matriz dá `dashboard:read` global a todos;
- `updated_at` não é mantido em `equipments` e `services`;
- `sgs_app` com DELETE;
- faltam índices em `equipments.unit_id` e `services.equipment_id`;
- as views não são usadas pela API;
- o teste e2e de TLS fica fora do CI;
- `.env.example` desatualizado;
- não há login.

### Requisitos
**Atendidos:**
- BD Etapa 2 (integridade);
- BD Etapa 4 (anti-join, FULL OUTER JOIN, views, índices sem a prova);
- BD Etapa 5 completa no banco;
- RBAC;
- audit trail;
- TLS.

**Parciais:**
- Etapa 3 (CRUD só de criação, 2 de 4 consultas);
- subconsultas;
- 30 tuplas.

**Não atendidos:**
- CRUD de 4 tabelas;
- catálogo de consultas;
- login;
- LDAP/OIDC;
- S3;
- governança.

---

## C. `feat/003-interface-dashboard` (ViniciusVbm, 3 commits, 26/10/2026)

**Objetivo aparente:** entregar as Etapas 2 e 3 de Banco de Dados com um esquema próprio em português, seed com 30 tuplas, CRUD em SQL bruto e um dashboard em JSON.

**Base:** `d67bb0f`, a `main` de 03/10, 44 commits atrás.

**Histórico:**
- `9245d4f` (o conteúdo é idêntico ao de `7fd3f05`, do PR #12, que já está na `main`; o commit em si não está);
- `4736f81` (Etapa 02);
- `8e16b17` (Etapa 03).

### Arquivos
São 97 arquivos e cerca de 5,6 mil linhas.

**Criados:**
- `src/resources/seeds/1_SQL_Criacao_Tabelas.sql` e `2_SQL_Insercao_Dados.sql`;
- `consultas_etapa3.sql`;
- `migrations/versions/0002_etapa2_tabelas.py` e `0003_etapa3_legado.py`;
- `docs/relatorio-etapa2-banco.md`;
- `src/core/session.py`;
- `src/modules/{access,dashboard,registry}/**` e partes de `identity`;
- `src/tools/seed_db.py`;
- `get-docker.sh`;
- 10 arquivos de teste.

**Modificados:**
- `Makefile`, `docker/Dockerfile`, `pyproject.toml`;
- `src/main.py`, `src/core/errors.py`;
- `audit/domain/entry.py`, `audit/infrastructure/*`;
- `steering/structure.md`;
- **28 arquivos de spec**: todo `Status: Rascunho` virou `Aprovado`, inclusive `_templates`.

Nenhum arquivo foi removido.

### Banco de dados
Tabelas `PERFIL`, `UNIDADE_SAUDE`, `USUARIO`, `EQUIPAMENTO` e `ALTERACAO`:
- PKs `INTEGER GENERATED ALWAYS AS IDENTITY`.
- 5 ON UPDATE CASCADE e 1 ON DELETE SET NULL (`USUARIO.IdUnidade`, linhas 46-49 de `1_SQL_Criacao_Tabelas.sql`).
- CHECKs de CNES (7 dígitos), CEP, telefone, e-mail, tipo, status e quantidade (0 a 5000).
- DEFAULT `CURRENT_TIMESTAMP`.

**Seed:** PERFIL 30, UNIDADE_SAUDE 30, USUARIO 30, EQUIPAMENTO 30, ALTERACAO 31 linhas. **Todas as tabelas têm 30 ou mais.** A migração `0003_etapa3_legado` adiciona `unaccent`, a função `normalizar_unidade_saude_etapa3()` e um trigger BEFORE INSERT/UPDATE.

### Backend
- `GET`, `POST` e `PATCH` (só status, com `If-Match`) em `/api/v1/unidades`.
- CRUD completo de `/api/v1/equipamentos` (DELETE físico).
- `GET /api/v1/dashboard/resumo`.
- Tudo com `text()`.

### Consultas
`consultas_etapa3.sql` tem 4 consultas:

| Consulta | Estrutura |
|---|---|
| Unidades por categoria | UNION ALL, sem JOIN |
| Equipamentos por tipo e distrito | JOIN |
| Alterações por período | JOIN com `FILTER` |
| Alterações recentes | 2 JOINs |

Não há anti-join, FULL OUTER JOIN, subconsulta nem view.

### Segurança
**Falha grave:** o usuário é identificado pelo cabeçalho `X-User-Id`, sem credencial nenhuma. Em qualquer ambiente que não seja prod, quem envia o cabeçalho age como qualquer usuário (`src/modules/access/api/deps.py:20-36`). Em prod, tudo responde 401. A identidade da spec 002 é ignorada.

- As permissões são strings separadas por `;` em `PERFIL`.
- O seed tem um único hash bcrypt para os 30 usuários e segredos TOTP de mentira (`'GDD-01-TOTP'`).

### Auditoria
- Grava na tabela `alteracao` (de/para, usuário, motivo), não no `audit_log` encadeado da `main`.
- Equipamentos não são auditados.
- O commit provavelmente acontece depois da resposta, pela dependência sem `scope="function"`.

### Testes
- `tests/integration/test_etapa2_banco.py`: tabelas, contagem de 30, CASCADE, SET NULL, CHECKs.
- `tests/integration/test_etapa3_auth.py`.
- Testes unitários com mocks.
- `tests/architecture/test_rotas_etapa3.py`.

São 95 funções. **Não foram executadas nesta auditoria.** Pela leitura, os imports resolvem dentro da própria branch. Ao juntar com a `main`, quebrariam por colisão de migração e de identidade.

### Problemas
- Revisões `0002` e `0003` colidem com a `main` (0002_identity) e com a 011 (0003_access).
- `PATCH /equipamentos/{id}` com `quantidade: null` dá 500 (`registry/application/servicos.py:78`).
- `registry/infrastructure/tables.py:37` diverge da migração 0003.
- O SQL é carregado no import do módulo.
- `get-docker.sh` (instalador oficial do Docker) foi commitado.
- O status das specs foi trocado sem aprovação real.
- `steering/structure.md` foi alterado para aceitar nomes de tabela em português.

### Requisitos
**Atendidos:**
- BD Etapa 2 com 30 tuplas, CASCADE e SET NULL;
- scripts de criação e inserção.

**Parciais:**
- Etapa 3: 4 consultas com JOIN; CRUD de 2 tabelas, com unidade só por status.

**Não atendidos:**
- Etapas 4 a 6;
- autenticação real;
- audit trail encadeado.

---

## D. `feat/002-fundacao-vinicius` (ViniciusVbm, 2 commits, 26/10/2026)

**Objetivo:** primeira metade do trabalho de Vinicius: validação da auditoria e o esquema da Etapa 2.

São os commits `9245d4f` e `4736f81`, 30 arquivos, +2.182 linhas. A ponta é **`4736f81`**; o `9245d4f` é o pai. A branch é **subconjunto exato** da `feat/003-interface-dashboard`, que contém esses dois commits e mais `8e16b17`.

O conteúdo do `9245d4f` está na `main` como `7fd3f05` (PR #12): mesmo patch-id e arquivos idênticos. O commit em si não é ancestral da `main`.

Não há nada nela que não esteja na 003. **Não há o que aproveitar separadamente.** Está preservada na tag `arquivo/002-fundacao-vinicius`.
