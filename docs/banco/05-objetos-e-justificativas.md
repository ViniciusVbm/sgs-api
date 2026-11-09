# Objetos de banco e justificativas (Etapas 2 a 6)

Cada objeto tem um `.sql` próprio com cabeçalho de objetivo, justificativa, uso e requisito. Aqui fica o resumo, com o arquivo e o teste que o prova. Todos os testes citados passaram em 09/11/2026 (ver `docs/RELATORIO_VALIDACAO_FINAL.md`).

## Etapa 2 · Integridade
| Exigência | Onde | Teste |
|---|---|---|
| PK, FK, UNIQUE, CHECK, DEFAULT | `migrations/sql/0006/*.sql`, `0011_09/03-05` | `tests/integration/registry/test_schema_registry.py`, `tests/integration/db/test_ajustes_0011_09.py` |
| ON UPDATE CASCADE | `equipments.equipment_type_code → equipment_types(code)` (`0006/16_equipments.sql`) | `test_integridade.py::test_correcao_do_codigo_do_tipo_chega_aos_equipamentos`; pela API, `test_crud_vinculos.py::test_referencias_listar_criar_e_corrigir_codigo_com_cascata` |
| ON DELETE SET NULL | `services.equipment_id → equipments(id)` (`0006/17_services.sql`) | `test_integridade.py`; pela API, `test_crud_vinculos.py::test_equipamento_da_unidade_crud_completo_com_auditoria` |
| ON DELETE RESTRICT | `equipments.unit_id`, `services.unit_id` | `test_integridade.py::test_unidade_com_vinculos_nao_e_apagada` |
| Sequências | `smallserial` nas referências; `GENERATED ALWAYS AS IDENTITY` em `audit_log` e `db_change_log` | dicionário de dados |
| 30 tuplas | ver [06-trinta-tuplas.md](06-trinta-tuplas.md) | `tests/integration/tools/test_seed_demo.py`, `test_sql_bd.py` |

## Etapas 3 e 4 · Consultas
| Consulta | Técnica | Arquivo | Rota | Teste |
|---|---|---|---|---|
| Unidades sem serviço | **anti join** (`LEFT JOIN … WHERE s.id IS NULL`) | `dashboard/…/units_without_services.sql` | `GET /api/v1/dashboard/consultas/unidades-sem-servico` | `test_consultas_qualidade.py` |
| Conciliação unidade × equipamento | **FULL OUTER JOIN** | `unit_equipment_reconciliation.sql` | `…/conciliacao-unidade-equipamento` | `test_consultas_qualidade.py` |
| Distritos com mais unidades sem CNES que a rede | **subconsulta** escalar no HAVING | `districts_cnes_above_network.sql` | `…/distritos-sem-cnes-acima-da-rede` | `test_painel.py` |
| Unidades com serviço fora do CNES | **subconsulta** correlacionada (EXISTS) | `units_with_services_outside_cnes.sql` | `…/unidades-com-servico-fora-do-cnes` | `test_painel.py` |
| Unidades por categoria (Etapa 3, da 003) | UNION ALL de agregações sobre a view | `units_by_category.sql` | `…/unidades-por-categoria` | `test_painel.py` |
| Equipamentos por tipo e distrito (Etapa 3, da 003) | JOIN de 5 tabelas, GROUP BY, SUM | `equipments_by_type_district.sql` | `…/equipamentos-por-tipo-e-distrito` | `test_painel.py` |
| Alterações por período (Etapa 3, da 003) | view + `count(*) FILTER` + subconsulta IN | `changes_by_period.sql` | `…/alteracoes-por-periodo` | `test_painel.py` |
| Alterações recentes (Etapa 3, da 003) | view com 4 JOINs | `recent_changes.sql` | `…/alteracoes-recentes` | `test_painel.py` |
| Resumo da rede | agregações e subconsultas escalares | `summary_quality.sql`, `summary_changes.sql` | `GET /api/v1/dashboard/resumo` | `test_painel.py::test_resumo_da_rede` |

Todas aplicam o **escopo de leitura** do usuário por um fragmento fixo de parâmetros (`:scope_*`) e aceitam filtros validados (distrito, tipo, área; 422 se inexistente). O catálogo `GET /api/v1/dashboard/consultas` lista cada uma com justificativa, parâmetros, colunas, permissão e gráfico sugerido.

## Etapa 4 · Views e índices
| Objeto | Justificativa | Arquivo | Teste |
|---|---|---|---|
| `vw_unit_inventory` | Definição única do inventário: 3 INNER JOINs (tipo, área, distrito) e 2 LEFT JOINs com agregados (equipamentos; serviços e serviços fora do CNES). Usa `fn_registration_status`. Sem dado pessoal (LGPD). `security_invoker` | `migrations/sql/0011_04/01` | `tests/integration/db/test_views.py`; pela API, `test_painel.py::test_inventario_pela_view_sem_dado_pessoal` |
| `vw_unit_history` | Histórico das unidades com 4 JOINs (unidade, tipo, distrito, autor), incluindo eventos de equipamentos e serviços | `0011_04/02` | `test_views.py`; pela API, `test_consulta_trilha.py` |
| `ix_audit_log_entity` (entity_type, entity_id, occurred_at DESC) | Histórico de uma unidade, o mais recente primeiro | `0011_03/06` | `tests/integration/db/test_indices.py` (**Index Scan** com 1.000 unidades; [planos](planos-indices.txt)) |
| `ix_services_unit_id` | Serviços de uma unidade; anti join e EXISTS | `0011_03/07` | `test_indices.py` (**Bitmap Index Scan**) |
| `ix_equipments_unit_id`, `ix_services_equipment_id` | FKs RESTRICT e SET NULL sem varredura | `0011_09/01-02` | `test_ajustes_0011_09.py` |
| `ix_health_units_name_normalized_trgm` (GIN) | Busca sem acento por trecho do nome | `0006/15` | `test_crud_unidades.py::test_lista_paginada_com_busca_sem_acento_e_filtros` |

A T9 pedia o EXPLAIN no cabeçalho dos `.sql` dos índices. Esses arquivos pertencem a migrações já aplicadas e não são editados; a evidência fica em `planos-indices.txt` e é regenerada por `SGS_PLANOS_SAIDA=... pytest -m slow tests/integration/db/test_indices.py`.

## Etapa 5 · Funções, procedures e triggers
| Objeto | Justificativa | Arquivo | Teste |
|---|---|---|---|
| `fn_normalize_name(text)` | Normalização única do nome (sem acento, caixa e espaços), base da unicidade e da busca. IMMUTABLE, usada na coluna gerada | `0006/03` | `test_normalizacao.py` |
| `fn_registration_status(health_units)` | **Estrutura condicional** (IF/ELSIF): inativa → com pendências → sem CNES → regular | `0011_03/08` | `test_situacao_cadastral.py` |
| `sp_deactivate_unit(uuid, OUT, OUT)` | **Atualiza dados**: trava e desativa; SQLSTATE `SGS01` se não existe; idempotente | `0011_06/01` | `test_sp_deactivate_unit.py`; pela API, `test_crud_unidades.py::test_desativar_pela_procedure_audita_uma_vez` |
| `sp_ensure_monthly_partitions(regclass, int)` | **CURSOR** explícito sobre os meses: cria as partições que faltam do log, sem apagar nada | `0011_08/01` | `test_particoes.py`; pela API, `GET /api/v1/auditoria/banco/particoes` |
| `trg_health_units_version` | Incrementa a versão (ETag/If-Match) em toda alteração real, inclusive fora da API | `0011_05` | `test_versao_trigger.py`; `test_crud_unidades.py::test_alteracao_fora_da_api_invalida_o_etag` |
| `trg_registry_change_log` | **Atualiza tabela de log** (`db_change_log`) em toda escrita de unidade, equipamento e serviço, mascarando o nome do gestor | `0011_07` | `test_log_banco.py`; pela API, `test_consulta_trilha.py::test_log_do_banco_mostra_alteracao_fora_da_api` |
| `trg_set_updated_at` | Mantém `updated_at` nas tabelas escritas com SQL à mão | `0011_09/06-14` | `test_ajustes_0011_09.py` |

## Etapa 6 · CRUD e interface
CRUD com inclusão, alteração e exclusão (lógica ou física) em **seis tabelas** pela API: `health_units` (exclusão lógica pela procedure), `equipments`, `services` (exclusão física), `unit_types`, `equipment_types` e `service_types` (desativação). Testes: `tests/integration/registry/test_crud_unidades.py` e `test_crud_vinculos.py`. A interface visual é o front em HTML, integrado à parte (`docs/frontend-integracao.md`).
