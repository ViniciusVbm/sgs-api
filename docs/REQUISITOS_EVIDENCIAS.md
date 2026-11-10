# Requisitos acadêmicos × evidências

**Status:**
- ✅ implementado e testado (teste executado e aprovado em 09/11/2026);
- 🟡 parcial;
- ⬜ pendente;
- ➖ não aplicável ou fora do escopo técnico, com justificativa.

Caminhos de teste relativos a `tests/`.

## Banco de Dados · Etapa 1
| Requisito | Implementação | Arquivos/evidências | Teste | Status |
|---|---|---|---|---|
| Minimundo | Texto do domínio | `docs/banco/01-minimundo.md` | — (documento) | ✅ |
| Modelo conceitual | DER (Mermaid) | `docs/banco/02-modelo-conceitual.md` | — | ✅ |
| Modelo lógico / esquema relacional | Tabelas, PK, FK, regras | `docs/banco/03-modelo-logico.md` | — | ✅ |
| Dicionário de dados | Gerado do metadata, igual às migrações | `docs/banco/04-dicionario-dados.md` | `integration/test_migracoes_sincronizadas.py` | ✅ |
| Coerência modelo × banco | Metadata sincronizado com a cadeia até a 0011_09 | idem | idem | ✅ |

## Banco de Dados · Etapa 2
| Requisito | Implementação | Arquivos/evidências | Teste | Status |
|---|---|---|---|---|
| Scripts de criação | DDL único | `make sql-bd` → `build/sql-bd.sql`; `migrations/sql/**` | `integration/tools/test_sql_bd.py` (banco vazio) | ✅ |
| Scripts de inserção | INSERTs dos dados de demonstração | `build/sql-bd-insercao.sql`; `seeds/demo/*.json` | `test_sql_bd.py`, `integration/tools/test_seed_demo.py` | ✅ |
| CHECK, DEFAULT, UNIQUE | Status, quantidade, pendências, CNES e nome únicos | `migrations/sql/0006/*`, `0011_09/03-05` | `integration/registry/test_schema_registry.py`, `integration/db/test_ajustes_0011_09.py` | ✅ |
| PK e FK | Todas as tabelas | dicionário | `integration/registry/test_integridade.py` | ✅ |
| ON UPDATE CASCADE | `equipments.equipment_type_code` | `0006/16_equipments.sql` | `test_integridade.py`; `integration/registry/test_crud_vinculos.py::test_referencias_listar_criar_e_corrigir_codigo_com_cascata` | ✅ |
| ON DELETE SET NULL | `services.equipment_id` | `0006/17_services.sql` | `test_integridade.py`; `test_crud_vinculos.py::test_equipamento_da_unidade_crud_completo_com_auditoria` | ✅ |
| Sequências | `smallserial`, identity | dicionário | — | ✅ |
| 30 tuplas por tabela | 37/31/35/30/30 nas de negócio | `docs/banco/06-trinta-tuplas.md` | `test_seed_demo.py` | 🟡 domínios fechados com a quantidade real (D1; o professor deve confirmar) |

## Banco de Dados · Etapa 3
| Requisito | Implementação | Arquivos/evidências | Teste | Status |
|---|---|---|---|---|
| Interface inicial / dashboard (tela) | Front em HTML, fora do repositório | `docs/frontend-integracao.md` | — | ⬜ integração do front pendente |
| Dashboard (dados) | `GET /dashboard/resumo`, catálogo, inventário | `src/modules/dashboard/` | `integration/dashboard/test_painel.py` | ✅ |
| CRUD em 2 tabelas ou mais | 6 tabelas (§ Etapa 6) | `src/modules/registry/` | `test_crud_unidades.py`, `test_crud_vinculos.py` | ✅ |
| Gráficos estatísticos | Dados agregados e gráfico sugerido no catálogo | `dashboard/domain/catalogo.py` | `test_painel.py` | 🟡 os gráficos são desenhados pelo front |
| 4 consultas ou mais, com 1 JOIN ou mais | 8 consultas no catálogo, mais o resumo | `dashboard/infrastructure/sql/*.sql` | `test_painel.py`, `integration/dashboard/test_consultas_qualidade.py` | ✅ |
| Backend integrado ao SGBD; SQL explícito | `text()` com arquivos `.sql` (ADR-0009) | `src/core/sql.py` | todos os de integração | ✅ |

## Banco de Dados · Etapa 4
| Requisito | Implementação | Arquivos/evidências | Teste | Status |
|---|---|---|---|---|
| Anti join | Unidades sem serviço | `units_without_services.sql` | `test_consultas_qualidade.py` | ✅ |
| FULL OUTER JOIN | Conciliação unidade × equipamento | `unit_equipment_reconciliation.sql` | `test_consultas_qualidade.py` | ✅ |
| 2 subconsultas | HAVING escalar; EXISTS correlacionado | `districts_cnes_above_network.sql`, `units_with_services_outside_cnes.sql` | `test_painel.py` | ✅ |
| 2 views com 3 JOINs ou mais e justificativa | `vw_unit_inventory`, `vw_unit_history` | `0011_04/*`; `docs/banco/05-objetos-e-justificativas.md` | `integration/db/test_views.py`; `test_painel.py`; `integration/audit/test_consulta_trilha.py` | ✅ |
| 2 índices novos e justificados | `ix_audit_log_entity`, `ix_services_unit_id` (mais 2 na 0011_09) | `0011_03/06-07`, `0011_09/01-02` | `integration/db/test_privilegios.py`, `test_ajustes_0011_09.py` | ✅ |
| Uso efetivo dos índices | EXPLAIN com 1.000 unidades | `docs/banco/planos-indices.txt` | `integration/db/test_indices.py` (slow) | ✅ |

## Banco de Dados · Etapa 5
| Requisito | Implementação | Arquivos/evidências | Teste | Status |
|---|---|---|---|---|
| 2 funções com justificativa | `fn_normalize_name`, `fn_registration_status` | `0006/03`, `0011_03/08` | `test_normalizacao.py`, `test_situacao_cadastral.py` | ✅ |
| Função com estrutura condicional | `fn_registration_status` (IF/ELSIF) | idem | idem | ✅ |
| 2 procedures | `sp_deactivate_unit`, `sp_ensure_monthly_partitions` | `0011_06/01`, `0011_08/01` | `test_sp_deactivate_unit.py`, `test_particoes.py` | ✅ |
| Procedure que atualiza dados | `sp_deactivate_unit`, também pela API | `registry/infrastructure/sql/call_sp_deactivate_unit.sql` | `test_crud_unidades.py::test_desativar_pela_procedure_audita_uma_vez` | ✅ |
| Procedure com CURSOR | `sp_ensure_monthly_partitions` | `0011_08/01` | `test_particoes.py` | ✅ |
| 2 triggers | `trg_health_units_version`, `trg_registry_change_log` (mais `trg_set_updated_at`) | `0011_05`, `0011_07`, `0011_09` | `test_versao_trigger.py`, `test_log_banco.py`, `test_ajustes_0011_09.py` | ✅ |
| Trigger que grava log | `trg_registry_change_log` → `db_change_log` | `0011_07/05` | `test_log_banco.py`; `test_consulta_trilha.py::test_log_do_banco_mostra_alteracao_fora_da_api` | ✅ |

## Banco de Dados · Etapa 6
| Requisito | Implementação | Arquivos/evidências | Teste | Status |
|---|---|---|---|---|
| CRUD em 4 tabelas ou mais | `health_units`, `equipments`, `services`, `unit_types`, `equipment_types`, `service_types` | `registry/api/*.py` | `test_crud_unidades.py`, `test_crud_vinculos.py` | ✅ |
| Efeitos de funções, procedures e triggers na interface | Situação cadastral no inventário; desativação; ETag pela versão; log do banco e partições na API | `dashboard`, `registry`, `audit/api` | `test_painel.py`, `test_crud_unidades.py`, `test_consulta_trilha.py` | ✅ (API); ⬜ tela |
| Consultas e views disponíveis, com filtros | Catálogo e rotas; filtros de distrito, tipo, área e situação (422 se inválido) | `dashboard/api/rotas.py` | `test_painel.py`, `test_consultas_qualidade.py` | ✅ |
| Indicadores estatísticos | Resumo: status, tipo, área, distrito, situação, qualidade, alterações em 7 e 30 dias | `summary_*.sql` | `test_painel.py::test_resumo_da_rede` | ✅ |
| Gráficos com dados reais e filtros interativos | Dados prontos; gráfico sugerido no catálogo | — | — | ⬜ depende do front |

## Projetos · Entrega 11
| Requisito | Implementação | Arquivos/evidências | Teste | Status |
|---|---|---|---|---|
| Testes automatizados, unitários e de integração | 888 casos | `tests/` | `make test-all`: 885 aprovados, 3 pulados | ✅ |
| Aceitação reproduzível | Roteiro do MVP | `integration/acceptance/test_roteiro_mvp.py` | idem | ✅ |
| Endpoints, CRUD, autenticação, autorização | 55 operações | `docs/api/endpoints.md` | `integration/registry/*`, `integration/identity/*`, `integration/access/*`, `architecture/test_rotas_protegidas.py` | ✅ |
| Regras de negócio | Unicidade, campos estruturais, If-Match, segregação | — | `test_crud_unidades.py`, `test_admin_atribuicoes.py` | ✅ |
| Banco | Integridade, privilégios, views, procedures, índices | — | `integration/db/*`, `integration/registry/*` | ✅ |
| E2E, Docker e TLS | Compose isolado | — | `e2e/test_tls_banco.py` (6) | ✅ |
| Scripts e instruções de teste | `Makefile`, `docs/instalacao.md` | — | — | ✅ |
| Documentação dos resultados | `docs/RELATORIO_VALIDACAO_FINAL.md` § 7 | — | — | ✅ |
| Qualidade do repositório | ruff, mypy strict, import-linter, bandit, pip-audit | `pyproject.toml` | `make check` | ✅ (CI do GitHub bloqueado; rodado localmente) |

## Segurança e Auditoria
| Requisito | Implementação | Arquivos/evidências | Teste | Status |
|---|---|---|---|---|
| Cadastro e classificação de fornecedores | Documental (D5) | `docs/governanca/01-fornecedores.md` | — | ✅ (documento) |
| Matriz probabilidade × impacto | 5 × 5 | `docs/governanca/02-matriz-de-riscos.md` | — | ✅ |
| Registro de riscos (interrupção de TI, cadeia de fornecedores) | R01 a R12, com controles e evidência | `docs/governanca/03-registro-de-riscos.md` | os testes citados em cada risco | ✅ |
| ISO 38500 e COBIT 2019 APO10 | Mapeamento com lacunas | `docs/governanca/04-iso38500-cobit-apo10.md` | — | ✅ (sem declarar conformidade) |
| LGPD (princípios técnicos) | Minimização, mascaramento, cifra, TLS | `docs/governanca/05-lgpd-tecnico.md` | `test_views.py`, `test_crud_unidades.py::test_trilha_mascara_o_nome_do_gestor_e_grava_o_papel` | 🟡 técnico ok; processos (titular, RIPD, DPO) fora do repositório |
| Audit trail: usuário, data e hora, ação, antes e depois, rastreabilidade | `audit_log` encadeado, mais `actor_roles` | `src/modules/audit/` | `test_audit_chain.py`, `test_audit_immutable.py`, `test_consulta_trilha.py` | ✅ |
| Controle de acesso aos registros | Histórico no escopo; trilha geral global; eventos de acesso só para `auditoria:read_acessos` | `audit/application/consultar.py` | `test_consulta_trilha.py` | ✅ |
| Medidas de mitigação e continuidade | Colunas do registro de riscos | doc 03 | — | 🟡 backup operacional fora do repositório |

## IAM
| Requisito | Implementação | Arquivos/evidências | Teste | Status |
|---|---|---|---|---|
| Usuários, papéis, permissões e RBAC com escopo | 7 papéis, 17 permissões, 4 níveis | `0003_access.py`, `access/domain/authorization.py` | `integration/access/*` | ✅ |
| Autenticação segura | Argon2id, TOTP, ES256, refresh rotativo, bloqueio, rate limit | `src/modules/identity/` | `integration/identity/*` | ✅ |
| Autorização no backend e proteção de rotas | `require()`, deny by default | `access/api/deps.py` | `test_require.py`, `test_rotas_protegidas.py` | ✅ |
| Gerenciamento de credenciais | Chaves versionadas, fora do Git, recusadas se de exemplo em prod | `src/core/config.py`, `src/tools/*_keys.py` | `unit/core/test_config.py` | ✅ |
| Grupos e sincronização | `group_role_mappings` existe (sem FK em `group_id`, sem rotas, 0 registros) e `role_assignments` aceita origem `group`; faltam `groups`, `user_groups`, `directory_sync_runs`, o cadastro de mapeamentos (003/T8) e a sincronização (004) | `0003_access.py` | — | ⬜ specs 003/T8 e 004 |
| LDAP / OIDC | — | `specs/004-*` (Rascunho) | — | ⬜ spec 004 |
| Persistência local de identidades externas | `users.source` (`local`/`ldap`/`oidc`), `external_id` e `synced_at`; unicidade e CHECK `credencial_conforme_origem` no banco e no domínio; o login local recusa conta externa. Faltam busca por `external_id`, upsert e preenchimento do `synced_at` (004/T3, T7) | `0002_identity.py`, `identity/domain/users.py`, `identity/application/login.py` | `unit/identity/test_users.py` (regras de origem); usuários `ldap` gravados em `integration/access/test_permissoes_efetivas.py` | 🟡 estrutura pronta |
| Exportação para S3 | — | `specs/005-*` (Rascunho) | — | ⬜ spec 005 |
