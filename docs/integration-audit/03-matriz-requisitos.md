# 03 · Matriz de requisitos

## Registro de execução dos testes
Há três momentos que não devem ser confundidos:

| Momento | O que foi feito | Resultado |
|---|---|---|
| Auditoria inicial (09/11/2026, manhã) | **nenhum teste executado**; a matriz foi montada lendo o código e os testes existentes | — |
| Validação técnica (09/11/2026, tarde), commit **`556599f`** (`feat/011-integracao`), extraído com `git archive` para uma pasta temporária, Python 3.13 via `uv sync --frozen`, PostgreSQL 17 por testcontainers | `make check` (ruff, ruff format, mypy, import-linter, `pytest -m "not slow"`) | **646 casos aprovados**, 0 falhas; 5 casos `slow` fora desta execução |
| | `pytest` dos 9 arquivos das Etapas 4 e 5 (`test_normalizacao`, `test_situacao_cadastral`, `test_sp_deactivate_unit`, `test_particoes`, `test_versao_trigger`, `test_log_banco`, `test_integridade`, `test_views`, `test_consultas_qualidade`) | **84 aprovados**. É um **subconjunto** dos 646 (são testes de integração não `slow`), rodado de novo para dar evidência nominal; não se soma aos 646 |
| | `pytest -m slow tests/e2e` (TLS do compose, num projeto Docker isolado) | **5 aprovados**; são os 5 que ficaram fora do `make check` |

- **Total distinto executado e aprovado no `556599f`:** 646 + 5 = **651 casos**, que é o total coletado.
- **Por que 269 funções viram 651 casos:** a contagem estática conta `def test_*`; o pytest multiplica as funções parametrizadas (por exemplo, `tests/unit/access/test_pode_matriz.py` gera mais de 100 casos a partir de poucas funções).
- **Não executado:** os testes da `feat/003-interface-dashboard` (95 funções); `make test-all` como comando único (os dois grupos acima equivalem a ele); `alembic downgrade base` (não há teste para isso).

## Como ler
**Status:**
- **IV**: implementado e validado. Há teste automatizado que comprova, e ele **foi executado e aprovado** no commit `556599f` (ver o Registro de execução acima). Na versão inicial desta matriz, IV significava só "há teste que comprova", sem execução; a validação técnica confirmou todos os IV da 011.
- **INV**: implementado, mas não validado.
- **PI**: parcialmente implementado.
- **NI**: não implementado.
- **BDE**: bloqueado por dependência externa.
- **FET**: fora do escopo técnico.

**Coluna "Onde":**
- `main`
- `011` = `feat/011-integracao` (proposta como base da versão final)
- `003V` = `feat/003-interface-dashboard`

O status vale para a **versão consolidada proposta**, isto é, `main` mais a 011.

**Coluna "Fecha com":** a tarefa da spec que conclui o requisito.

**Interface, dashboard visual e gráficos:** o front em HTML existe fora do repositório e será integrado depois. Por isso a parte visual está marcada como **BDE**. A parte da API que alimenta o front é avaliada à parte.

## 5.1 Banco de Dados · Etapa 1
| Requisito | Status | Onde | Evidência | Fecha com |
|---|---|---|---|---|
| Minimundo | NI | — | `grep -ri minimundo` sem resultado; só há o domínio em `steering/product.md` § Domínio | doc novo `docs/banco/01-minimundo.md` |
| Modelo conceitual (ER) | NI | — | não há DER conceitual; `docs/architecture/modelo-dados.md` já é físico | doc novo, Mermaid erDiagram conceitual |
| Modelo lógico | PI | main | `docs/architecture/modelo-dados.md` tem diagramas Mermaid e "colunas principais", parcialmente desatualizados em relação às migrações da 011 | atualizar a partir das migrações |
| Esquema relacional | INV | 011 | `migrations/sql/0006/*.sql`, `migrations/versions/*.py` | 011/T20 (arquivo único) |
| Dicionário de dados | NI | — | não existe | gerar do `information_schema` e de `pg_description` |
| Coerência modelo × banco | PI | 011 | `test_migracoes_sincronizadas.py` garante modelo SQLAlchemy = migrações; não há conferência dos documentos | revisar depois da T20 |

## 5.2 Banco de Dados · Etapa 2
| Requisito | Status | Onde | Evidência | Fecha com |
|---|---|---|---|---|
| Scripts de criação | PI | 011 | um `.sql` por objeto em `migrations/sql/**`, sem arquivo único (R11.2) | 011/T20 (`make sql-bd`, gera `build/sql-bd.sql`) |
| Scripts de inserção | PI | 011 / 003V | 011: só os seeds de referência (`0006/18-22_seed_*.sql`). 003V: `2_SQL_Insercao_Dados.sql`, em esquema incompatível | seed demo (010) mais T20 |
| CHECK | IV | 011 | `ck_health_units_status_valido`, `ck_health_units_pending_issues_nao_negativo`, CHECKs de escopo em `role_assignments`; `test_schema_registry.py` | — |
| DEFAULT | IV | 011 | `version 1`, `pending_issues 0`, `quantity 1`, `in_cnes false`, `clock_timestamp()` | — |
| UNIQUE | IV | 011 | `ix_health_units_cnes` (parcial), `ix_health_units_district_id_name_normalized`, `uq_*_code`; `test_criar_unidade.py` (409) | — |
| PK e FK | IV | 011 | todas as tabelas; `test_integridade.py` | — |
| ≥1 ON UPDATE CASCADE | IV | 011 | `equipments.equipment_type_code → equipment_types(code)` (`0006/16_equipments.sql:25`); `test_integridade.py` | — |
| ≥1 ON DELETE SET NULL | IV | 011 | `services.equipment_id → equipments(id)` (`0006/17_services.sql:28`); `test_integridade.py` | — |
| Sequências | IV | 011 | `SMALLSERIAL` nas referências; `db_change_log.id` como `GENERATED ALWAYS AS IDENTITY`; as tabelas de negócio usam uuid7 (decisão de projeto) | — |
| ≥30 tuplas por tabela | **NI** | (003V cumpre no esquema antigo) | 011: referências com 3 a 8 linhas (decisão U4 em `specs/011/requirements.md:126`); `health_units`, `equipments`, `services` e `users` sem seed | seed demo; **decisão** sobre domínios fechados |

## 5.3 Banco de Dados · Etapa 3
| Requisito | Status | Onde | Evidência | Fecha com |
|---|---|---|---|---|
| Interface inicial | BDE | front HTML | nenhum front no repositório | integração do front |
| Dashboard (visual) | BDE | front HTML | — | integração do front |
| Dashboard (API) | PI | 011 | duas consultas em `/api/v1/dashboard/consultas/*`; sem `/dashboard/resumo` | 009, 011/T19 |
| CRUD (I/U/D) em ≥2 tabelas | **PI** | 011 | só `POST /api/v1/unidades` (`registry/api/unidades.py`); 003V tinha equipamentos completos em outro esquema | 006/T4 a T9 |
| Gráficos estatísticos | BDE | front HTML | a API deve devolver séries agregadas (009) | 009 mais front |
| Visualização dos resultados | PI | 011 | JSON paginado | 011/T19 |
| ≥4 consultas | PI | 011 | 2 consultas expostas (anti-join e full outer join); 003V tem 4 que precisam ser reescritas | 011/T12 e reescrita das 4 da 003V |
| ≥1 JOIN | IV | 011 | `units_without_services.sql`, `unit_equipment_reconciliation.sql`; `test_consultas_qualidade.py` | — |
| Backend integrado ao SGBD | IV | 011 | asyncpg e SQLAlchemy; testes de integração com Postgres 17 | — |
| SQL explícito | IV | 011 | ADR-0009; `src/core/sql.py`; `*/infrastructure/sql/*.sql` | — |

## 5.4 Banco de Dados · Etapa 4 (prazo 13/11/2026)
| Requisito | Status | Onde | Evidência | Fecha com |
|---|---|---|---|---|
| Anti-join | IV | 011 | `dashboard/infrastructure/sql/units_without_services.sql` (`LEFT JOIN services … WHERE s.id IS NULL`); `test_consultas_qualidade.py` | — |
| FULL OUTER JOIN | IV | 011 | `unit_equipment_reconciliation.sql`; `test_consultas_qualidade.py` | — |
| 2 subconsultas | PI | 011 | há `IN (SELECT …)` na conciliação e `EXISTS` em `district_exists.sql` e `unit_type_exists.sql`, mas as 2 consultas de negócio da R2.3 e R2.4 ainda não existem | 011/T12 |
| 2 views elaboradas | IV | 011 | `vw_unit_inventory` e `vw_unit_history` (`migrations/sql/0011_04/*`); `tests/integration/db/test_views.py` | — |
| ≥3 JOINs nas views | IV | 011 | inventário: 3 INNER e 2 LEFT; histórico: 4 | — |
| Justificativa das views | INV | 011 | cabeçalho dos `.sql` e `specs/011/requirements.md` R4 | doc da T20 |
| Views usadas pela API | NI | — | nenhuma rota lê as views | 011/T13, T14 |
| 2 índices novos e justificados | INV | 011 | `ix_audit_log_entity`, `ix_services_unit_id` com cabeçalho de justificativa (`0011_03/06-07`) | — |
| Uso efetivo dos índices | **NI** | — | a prova com EXPLAIN em volume está pendente (o cabeçalho remete à T9) | 011/T9 (`tests/integration/db/test_indices.py -m slow`) |

## 5.5 Banco de Dados · Etapa 5 (prazo 13/11/2026)
Todos os testes citados nesta seção estão entre os 84 rodados nominalmente na validação de 09/11/2026, e todos passaram.
| Requisito | Status | Onde | Evidência | Fecha com |
|---|---|---|---|---|
| 2 funções com justificativa | IV | 011 | `fn_normalize_name` (`0006/03`), `fn_registration_status` (`0011_03/08`); `test_normalizacao.py`, `test_situacao_cadastral.py` | — |
| ≥1 função condicional | IV | 011 | `fn_registration_status` com IF/ELSIF/ELSE | — |
| 2 procedures | IV | 011 | `sp_deactivate_unit` (`0011_06/01`), `sp_ensure_monthly_partitions` (`0011_08/01`) | — |
| Procedure que atualiza dados | IV | 011 | `sp_deactivate_unit` (UPDATE status); `test_sp_deactivate_unit.py` | — |
| Procedure com CURSOR | IV | 011 | `sp_ensure_monthly_partitions`, CURSOR `c_meses`; `test_particoes.py` | — |
| 2 triggers | IV | 011 | `trg_health_units_version`, `trg_registry_change_log` (em 3 tabelas); `test_versao_trigger.py`, `test_log_banco.py` | — |
| Trigger que grava log | IV | 011 | `trg_registry_change_log` → `db_change_log` | — |

## 5.6 Banco de Dados · Etapa 6 (prazo 13/11/2026)
| Requisito | Status | Onde | Evidência | Fecha com |
|---|---|---|---|---|
| Dashboard final (visual) | BDE | front HTML | — | front |
| CRUD em ≥4 tabelas | **NI** | — | só a criação de unidade | 006/T4 a T9 (unidades, equipamentos, serviços, referências) |
| Interface com efeitos de funções, procedures e triggers | NI (API) / BDE (tela) | — | sem rota de desativação (procedure), versão (trigger), log do banco ou situação cadastral (função) | 011/T13, T15, T16, T17 |
| Consultas e views disponíveis | PI | 011 | 2 de 6 expostas | 011/T12 a T14, T19 |
| Filtros nas consultas | IV | 011 | `distrito`, `tipo` com 422 para valor inválido; `test_consultas_qualidade.py` | — |
| Indicadores estatísticos | NI | — | não há `/dashboard/resumo` | 009 (Rascunho) |
| Gráficos com dados reais | BDE | front | a API precisa do seed demo | 010 mais front |
| Filtros interativos | BDE | front | — | front |

## 5.7 Projetos · Entrega 11 (prazo 21/11/2026 às 09h)
| Requisito | Status | Onde | Evidência | Fecha com |
|---|---|---|---|---|
| Testes automatizados | IV | main + 011 | 269 funções, 651 casos; `make check` com 646 aprovados e e2e com 5 aprovados no `556599f` em 09/11/2026 | — |
| Testes de integração | IV | 011 | testcontainers com `postgres:17` (`tests/integration/postgres.py`) | — |
| Testes de aceitação reproduzíveis | NI | — | não há roteiro nem `tests/acceptance` | doc 09 |
| Validação de endpoints | PI | 011 | `test_criar_unidade.py`, `test_require.py`, `test_contrato_openapi.py` | crescer com a 006 |
| Testes de CRUD | PI | 011 | só criação | 006 |
| Testes de autenticação e autorização | PI | 011 | autorização forte (`test_require.py`, 12 casos); sem login para testar | 002/T3 |
| Testes de regras de negócio | IV | 011 | normalização, unicidade, situação cadastral, versão | — |
| Testes de banco | IV | 011 | integridade, privilégios, views, partições, log | — |
| Organização dos scripts | IV | main | `Makefile` (`check`, `test-all`, `openapi`, `migrate`) | — |
| Instruções para rodar os testes | PI | main | `AGENTS.md`, `steering/testing.md`, `README.md` | README de testes |
| Documentação de resultados | NI | — | — | `docs/testes/resultados-E11.md` |
| Qualidade do repositório | IV | main | ruff, mypy strict, import-linter, bandit, pip-audit no CI | — |

## 5.8 Segurança e Auditoria
| Requisito | Status | Onde | Evidência | Fecha com |
|---|---|---|---|---|
| Cadastro e classificação de fornecedores | NI | — | `grep -ri fornecedor` sem resultado | doc ou módulo `governance` |
| Matriz de probabilidade × impacto | NI | — | sem resultado | doc de governança |
| Registro de riscos | NI | — | só existem seções "Riscos" de engenharia nas specs | doc de governança |
| Riscos de interrupção de TI | NI | — | — | doc de governança |
| Riscos de vazamento na cadeia de fornecedores | NI | — | — | doc de governança |
| Controles ISO 38500 | NI | — | `grep 38500` sem resultado | doc de governança |
| COBIT 2019 / APO10 | NI | — | sem resultado | doc de governança |
| Princípios técnicos da LGPD | PI | main + 011 | `FieldCipher` AES-256-GCM (`src/core/crypto.py`); view sem dado pessoal (R4.2); máscara de `manager_name` no `db_change_log`; redação de logs (`src/core/logging.py`); **`manager_name` sem máscara no `audit_log`** | correção mais doc LGPD |
| Audit trail | IV | main + 011 | `audit_log` com cadeia SHA-256, `audit_chain_head`; `test_audit_chain.py` | — |
| Logs de operações | IV | 011 | `db_change_log` por trigger; structlog com `request_id` | — |
| Usuário responsável | PI | 011 | `actor_user_id`, sessão, IP; **`actor_roles` vazio** | correção de `Ator.papeis` |
| Data e hora | IV | main | `occurred_at` em UTC | — |
| Registro das ações | IV | 011 | `unidade.criada`, `acesso.negado` | — |
| Valor anterior e posterior | IV | 011 | `changes` com `{campo, de, para}`; `db_change_log.changed_columns` | — |
| Rastreabilidade | IV | main | cadeia de hash; `test_audit_immutable.py` (5 casos) | — |
| Controle de acesso aos registros | INV | main | `REVOKE UPDATE/DELETE/TRUNCATE` em `audit_log` para `sgs_app`; sem rota de leitura com `auditoria:read` | 008 |
| Medidas de mitigação e continuidade | NI | — | — | doc de governança |

## 5.9 IAM
| Requisito | Status | Onde | Evidência | Fecha com |
|---|---|---|---|---|
| Arquitetura de identidade | INV | main | ADR-0003, `docs/architecture/arquitetura-conceitual.md` | — |
| Usuários | IV | main | `users` com `source` local/ldap/oidc; `test_repositories.py` | — |
| Grupos | **NI** | — | não há `groups` nem `user_groups`; só `group_role_mappings` (com `group_id` sem FK) | 004 |
| Papéis e permissões | IV | 011 | `roles`, `permissions`, `role_permissions` (7/17/51); `test_seed_matriz.py` | — |
| RBAC com escopo | IV | 011 | `access/domain/authorization.py` (`pode()`); `test_pode_matriz.py` | — |
| Autenticação | **NI** | — | não há rota de login nem Argon2 (002/T3); só a validação do token | 002/T3, T6, T8 |
| Autorização no backend | IV | 011 | `require()`; `test_require.py` | — |
| Proteção de rotas | PI | 011 | todas as rotas de negócio usam `require`; o teste de arquitetura que garante isso é a 003/T5, ainda aberta | 003/T5 |
| Integração LDAP | NI | — | sem ldap3; spec 004 em Rascunho | 004 |
| Integração OIDC | NI | — | sem Authlib; spec 004 em Rascunho | 004 |
| Sincronização de usuários e grupos | NI | — | — | 004 |
| Persistência em tabelas locais | PI | main | `users.external_id` pronto | 004 |
| Exportação para S3 | NI | — | sem boto3; spec 005 em Rascunho | 005 |
| Autenticação segura e credenciais | PI | main + 011 | ES256 com `kid`, chaves em secret do compose; `FieldCipher` com chaves versionadas; TLS no banco; sem Argon2, TOTP ou rate limit | 002/T3, T5, T7 |

## Placar
| Bloco | IV | INV | PI | NI | BDE |
|---|---|---|---|---|---|
| BD 1 | 0 | 1 | 2 | 3 | 0 |
| BD 2 | 7 | 0 | 2 | 1 | 0 |
| BD 3 | 3 | 0 | 4 | 0 | 3 |
| BD 4 | 4 | 2 | 1 | 2 | 0 |
| BD 5 | 7 | 0 | 0 | 0 | 0 |
| BD 6 | 1 | 0 | 1 | 3 | 3, mais 1 metade da tela |
| E11 | 6 | 0 | 4 | 2 | 0 |
| Seg/Aud | 6 | 1 | 2 | 8 | 0 |
| IAM | 4 | 1 | 3 | 6 | 0 |
