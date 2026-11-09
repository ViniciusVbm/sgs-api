# 09 · Plano de testes da versão final

## Níveis e comandos
| Nível | Onde | Ferramenta | Comando | Precisa de Docker |
|---|---|---|---|---|
| Unitário | `tests/unit/**` | pytest, hypothesis | `make check` (inclui `-m "not slow"`) | não |
| Arquitetura | `tests/architecture/**` | import-linter, comparação do OpenAPI | `make check` | não |
| Integração (API e banco) | `tests/integration/**` | pytest, testcontainers (`postgres:17`), httpx ASGI | `make test-all` | sim |
| Banco (objetos e planos) | `tests/integration/db/**`, `registry/**`, `audit/**` | SQL direto como `sgs_api` e como superusuário | `make test-all` | sim |
| E2E (compose) | `tests/e2e/**` (`slow`) | compose, TLS | `uv run pytest -m slow tests/e2e` | sim |
| Aceitação (novo) | `tests/acceptance/**` | httpx contra `https://localhost` com seed demo | `uv run pytest tests/acceptance` | sim |
| Estático e segurança | — | ruff, mypy strict, bandit, pip-audit | CI ou `uv run bandit -r src`, `uv run pip-audit` | não |

## Pré-condições
Unitários, integração e e2e **não precisam do compose**: o testcontainers sobe um PostgreSQL próprio, e o e2e usa um projeto compose isolado. O compose só é necessário para o roteiro de aceitação.
```bash
uv sync --frozen
mkdir -p secrets && uv run python -m src.tools.jwt_keys --output secrets/jwt-keys.json   # se ainda não existir
docker compose -f docker/compose.yml up -d --build --wait    # a API aplica as migrações na subida (dev)
docker compose -f docker/compose.yml exec api sgs-admin seed demo          # depois da I6 (comando ainda não existe)
docker compose -f docker/compose.yml exec api sgs-admin create-user ...    # depois da I10 (comando ainda não existe)
```
- **Impacto do `up --build`:** substitui os containers `sgs-api-*` em execução e reaproveita o volume do banco (doc 07, passo 1d).
- **Não usar `uv run alembic upgrade head` no host:** o banco não expõe porta e exige TLS com o nome `db`.

## Testes por requisito
| Requisito | Teste (existente ✔ ou a criar ✚) |
|---|---|
| CASCADE, SET NULL, RESTRICT | ✔ `tests/integration/registry/test_integridade.py` |
| CHECK, UNIQUE, DEFAULT | ✔ `test_schema_registry.py`, `test_criar_unidade.py` |
| 30 tuplas | ✚ `tests/integration/tools/test_seed_demo.py`: `SELECT count(*)` maior ou igual a 30 por tabela, e idempotência |
| Anti-join e FULL OUTER JOIN | ✔ `tests/integration/dashboard/test_consultas_qualidade.py` |
| Subconsultas | ✚ `tests/integration/dashboard/test_consultas_qualidade.py::test_distritos_cnes*` e `::test_fora_cnes*` (011/T12) |
| Views | ✔ `tests/integration/db/test_views.py`; ✚ `tests/integration/dashboard/test_inventario.py` (011/T13), `tests/integration/audit/test_historico_unidade.py` (011/T14, depende da 008) |
| Índices usados | ✚ `tests/integration/db/test_indices.py -m slow` (011/T9): EXPLAIN com 1.000 unidades, conferindo `ix_audit_log_entity` e `ix_services_unit_id` |
| Funções | ✔ `test_normalizacao.py`, `test_situacao_cadastral.py` |
| Procedures | ✔ `test_sp_deactivate_unit.py`, `test_particoes.py`; ✚ rota de desativação |
| Triggers e log | ✔ `test_versao_trigger.py`, `test_log_banco.py`, `test_log_banco_privilegios.py`; ✚ If-Match invalidado por alteração fora da API (011/T17) |
| CRUD de 4 tabelas | ✚ `test_{listar,atualizar,desativar}_unidade.py`, `test_equipamentos.py`, `test_servicos.py`, `test_referencias.py` (cada um com 201/200/204, 401, 403, 404, 409, 412/428, 422 e auditoria) |
| Catálogo e filtros | ✚ `test_catalogo.py`; ✔ filtros com 422 em `test_consultas_qualidade.py` |
| Indicadores | ✚ `test_resumo.py` |
| Login, refresh, logout | ✚ `tests/integration/identity/test_login.py` |
| RBAC | ✔ `tests/integration/access/*`, `tests/unit/access/*`; ✚ `tests/architecture/test_rotas_protegidas.py` |
| Audit trail | ✔ `test_audit_chain.py`, `test_audit_immutable.py`, `test_hash.py`; ✚ `test_verificacao_cadeia.py` (008) |
| `actor_roles` preenchido | ✚ em `test_sessao_de_negocio.py` |
| Privilégios mínimos | ✔ `tests/integration/db/test_privilegios.py`; ✚ sem DELETE em `health_units` |
| TLS no banco | ✔ `tests/e2e/test_tls_banco.py` |
| LDAP e OIDC | ✚ `tests/integration/directory/*` com slapd e Keycloak (P2) |
| S3 | ✚ `tests/integration/reports/*` com SeaweedFS (P2) |

## Roteiro de aceitação reproduzível (E11)
O arquivo `tests/acceptance/test_roteiro_mvp.py` roda contra o compose com o seed demo. Cada passo é uma asserção:

1. `GET /health/ready` devolve 200.
2. `POST /api/v1/auth/login` como GESTOR_DADOS devolve 200 e um token.
3. `GET /api/v1/unidades?distrito=…` devolve 200 com 30 ou mais unidades no total.
4. `POST /api/v1/unidades` devolve 201, e o `GET /unidades/{id}/historico` mostra `unidade.criada`.
5. `PATCH /api/v1/unidades/{id}` com `If-Match` devolve 200, a `version` sobe e o histórico mostra de/para.
6. `PATCH` com `If-Match` antigo devolve 412.
7. `POST /api/v1/unidades/{id}/desativar` devolve 200, e a situação cadastral (`fn_registration_status`) passa a `inativa` no inventário.
8. CRUD de equipamento e de serviço; o DELETE de equipamento deixa o serviço com `equipment_id NULL` (SET NULL).
9. `GET /api/v1/dashboard/consultas` (catálogo) e cada consulta com filtro.
10. `GET /api/v1/dashboard/resumo`.
11. Login como AUDITOR: `POST /unidades` devolve 403, e `acesso.negado` aparece na trilha.
12. `GET /api/v1/auditoria/verificacao` devolve "íntegra".
13. Sem token, qualquer rota de negócio devolve 401.

## Evidência dos resultados
- `make test-all` com `--junitxml=reports/junit.xml --cov=src --cov-report=html:reports/cov`.
- Os planos de execução vão em `docs/banco/indices.md`.
- O resumo vai em `docs/testes/resultados-E11.md`: data, commit, totais, cobertura, falhas conhecidas.
- Capturas do front ficam para quando ele for integrado.

## Critérios de saída
- `make check` e `make test-all` verdes no commit da entrega.
- Todos os requisitos do doc 03 marcados IV ou BDE, ou com justificativa registrada.
- O roteiro de aceitação passa num clone limpo.
