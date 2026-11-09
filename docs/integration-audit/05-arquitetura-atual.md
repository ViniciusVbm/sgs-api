# 05 · Arquitetura atual

Descreve o que existe hoje na `main` mais a `feat/011-integracao`, que é aplicável por fast-forward. Arquivos da 011 foram lidos com `git show origin/feat/011-integracao:<path>`.

## Estilo
**Monólito modular em FastAPI** (ADR-0001 e ADR-0002, ambos "Proposto"), Python 3.13, gerenciado por `uv`. O padrão é DDD em camadas por módulo:

```
src/
├── main.py                 # app factory: middlewares, handlers problem+json, routers
├── core/                   # infraestrutura transversal
│   ├── config.py           # Settings (pydantic-settings) por ambiente
│   ├── crypto.py           # FieldCipher AES-256-GCM com chaves versionadas (002/T1)
│   ├── db.py               # engine async, metadata, migrações no startup em dev
│   ├── sql.py              # carregador de .sql dos módulos (ADR-0009)        [011]
│   ├── escopo.py           # scope_filter, parametros_de_escopo               [011]
│   ├── paginacao.py                                                          [011]
│   ├── errors.py, problem.py, health.py, ids.py (uuid7), logging.py (structlog + redação),
│   └── request_context.py, security_headers.py
├── modules/
│   ├── audit/       domain(entry: cadeia de hash) · application(registrar) · infrastructure(SqlAuditStore)
│   ├── identity/    domain(users, sessions, tokens) · application(autenticacao, jwks) · api(deps: CurrentUser, jwks) · infrastructure
│   ├── access/      domain(authorization: pode(), escopos) · application(permissoes: cache) · api(deps: require()) · infrastructure   [011]
│   ├── registry/    domain(unidade) · application(unidades: criar) · api(unidades) · infrastructure(sql/*.sql)                     [011]
│   └── dashboard/   domain(consultas) · application · api(rotas) · infrastructure(sql/*.sql)                                    [011]
└── tools/  export_openapi.py · jwt_keys.py [011] · sgs_admin.py [011]
```

## Regras de camada (import-linter, `pyproject.toml`)
| Contrato | O que garante |
|---|---|
| `dominio-puro` | `src.modules.*.domain` não importa `src.core` (exceto `core.errors`), FastAPI, Starlette, SQLAlchemy, asyncpg, Alembic, structlog nem pydantic_settings |
| `dominios-independentes` | o domain de um módulo não importa o de outro |
| `camadas-dos-modulos` | dentro de cada módulo, api > application > domain |
| `aplicacao-sem-frameworks` | application não importa frameworks, drivers nem `core`, exceto `core.errors` |

Esses contratos rodam em `make check` (`lint-imports`) e em `tests/architecture/test_camadas.py`. Na 011 não há violação, e o mesmo vale para a 003V.

## Acesso a dados
- SQLAlchemy 2 async com asyncpg.
- As tabelas são declaradas em `*/infrastructure/tables.py`, para autogenerate e para o teste `test_migracoes_sincronizadas.py`.
- **As consultas de negócio são `.sql` explícitos** (ADR-0009, exigência da disciplina): `src/modules/*/infrastructure/sql/*.sql`, carregados por `src/core/sql.py`.
- Transação por requisição: a `SessaoDeNegocio` (`access/api/deps.py`) usa dependência com `scope="function"`, então o commit acontece antes da resposta. Auditoria e negócio ficam na mesma transação.

## Banco de dados
**PostgreSQL 17.** Migrações Alembic em `migrations/versions/`. Na 011, cada objeto é um `.sql` em `migrations/sql/<revisão>/NN_*.sql`, executado por `migrations/sql_loader.py` (`executar_sql`, uma instrução por arquivo, com modo offline).

**Cadeia:** 0001 → 0001_1 → 0002 → 0003 → 0003_1 → 0006 → 0011_05 → 0011_03 → 0011_06 → 0011_04 → 0011_07 → 0011_08.

**Papéis:**

| Papel | Tipo | Uso |
|---|---|---|
| dono das migrações | superusuário do container | aplica as migrações |
| `sgs_owner` | NOLOGIN | dono dos objetos SECURITY DEFINER (log do banco, partições); SELECT em 8 tabelas |
| `sgs_app` | NOLOGIN | privilégios de negócio; **sem** UPDATE, DELETE nem TRUNCATE em `audit_log`; sem DML nas views |
| `sgs_api` | LOGIN, membro de `sgs_app` | usuário da API (`docker/postgres/init/01-usuario-app.sql`) |

**Tabelas por domínio:**
- Auditoria: `audit_log`, `audit_chain_head`, `db_change_log` (particionada).
- Identidade: `users`, `sessions`, `refresh_tokens`.
- Acesso: `roles`, `permissions`, `role_permissions`, `role_assignments`, `group_role_mappings`.
- Cadastro: `districts`, `technical_areas`, `unit_types`, `equipment_types`, `service_types`, `health_units`, `equipments`, `services`.

**Objetos:**
- Views: `vw_unit_inventory`, `vw_unit_history`.
- Funções: `fn_normalize_name`, `fn_registration_status`.
- Procedures: `sp_deactivate_unit`, `sp_ensure_monthly_partitions`.
- Triggers: `trg_health_units_version`, `trg_registry_change_log`, `trg_roles_protect_system`, `audit_log_somente_insercao`.
- Os 7 índices estão listados no doc 02.

## Segurança
**Autenticação:**
- Tokens ES256 (P-256) com `kid` e rotação; JWKS em `/.well-known/jwks.json`.
- Access token de 15 minutos; o `CurrentUser` confere sessão e usuário a cada requisição.
- **Não há emissão de token por login** (002/T3 aberta).

**Autorização:**
- `require("recurso:acao")` nega por padrão.
- Escopo máximo por papel (Global, Área, Distrito, Unidade).
- Cache de 30 s invalidado por `users.authz_version`.
- 403 auditado como `acesso.negado`.

**Criptografia:**
- `FieldCipher` para campos sensíveis.
- TLS 1.2 ou mais entre API e banco (`verify-full`, CA própria gerada por `docker/postgres/gerar-certificados.sh`).
- HTTPS no Caddy.
- Cabeçalhos de segurança no middleware.

**Logs:**
- structlog com redação de segredos (`src/core/logging.py`) e `request_id`.
- O erro de banco não vaza valores (`test_erros_do_banco.py`).

**Auditoria:**
- Cadeia SHA-256 com `audit_chain_head FOR UPDATE`.
- Triggers de imutabilidade bloqueiam até o dono (`test_audit_immutable.py`).

## Implantação (`docker/compose.yml` na 011)
```
db-certs (alpine) ─► gera CA + cert do servidor ─► volume db-certs
db (postgres:17, ssl=on, pg_hba hostssl scram) ◄── api (FastAPI/uvicorn, DATABASE_SSL_MODE=verify-full, secret JWT)
proxy (caddy:2, HTTPS) ─► api
```
Não há LDAP, Keycloak, MinIO nem SeaweedFS. O comentário em `docker/compose.yml:2` remete às specs 004 e 005.

## Qualidade e CI
- `make check`: ruff check, ruff format --check, mypy (strict), lint-imports e `pytest -m "not slow"`.
- `make test-all`: todos os testes (precisa de Docker).
- `.github/workflows/ci.yml`:
  - job `quality`, com Postgres 17 como service, OpenAPI diff, bandit e pip-audit;
  - job `compose-smoke`.
- O GitHub Actions está bloqueado por ora; o ADR-0008 admite `make check` local registrado no PR.
- O contrato `contracts/openapi.yaml` é verificado por `tests/architecture/test_contrato_openapi.py`.

## Processo (SDD)
- `steering/*` traz as regras.
- `specs/NNN-*/{requirements,design,tasks}.md` só podem ser implementadas com os três arquivos aprovados.
- Há uma exceção provisória em `steering/sdd-workflow.md:30-31`: Rafael aprova sozinho as specs 003, 006 e 011.

**Status das specs:**

| Spec | Estado | Tarefas concluídas |
|---|---|---|
| 001 | aprovada | 9 de 9 |
| 002 | aprovada | 3 de 8 na 011 |
| 003 | aprovada | 4 de 8 na 011 |
| 006 | aprovada | 3 de 10 na 011 |
| 011 | aprovada | 10 de 20 na 011 |
| 004, 005, 007, 008, 009, 010 | **Rascunho** | — |

## Lacunas de arquitetura
- Não há front. Ele existe em HTML e será integrado depois.
- Não há módulo de relatórios (S3), de diretório (LDAP/OIDC) nem de governança.
- Não há seed de demonstração.
