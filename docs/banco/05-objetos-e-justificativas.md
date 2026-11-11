# Objetos de banco e justificativas (Etapas 2 a 6)

Cada objeto tem um `.sql` próprio com cabeçalho de objetivo, justificativa, uso e requisito. Aqui fica o resumo, com o arquivo e o teste que o prova. Os testes das Etapas 2 a 5 passaram em 09/11/2026 (ver `docs/RELATORIO_VALIDACAO_FINAL.md`); os da § Etapa 6, em 10/11/2026 (ver `specs/012-frontend/tasks.md`, T9 a T26).

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
| `trg_health_units_version` | Em toda alteração real de `health_units`, inclusive fora da API, incrementa a versão (ETag/If-Match) e grava o `updated_at` | `0011_05` | `test_versao_trigger.py`; `test_crud_unidades.py::test_alteracao_fora_da_api_invalida_o_etag` |
| `trg_registry_change_log` | **Atualiza tabela de log** (`db_change_log`) em toda escrita de unidade, equipamento e serviço, mascarando o nome do gestor | `0011_07` | `test_log_banco.py`; pela API, `test_consulta_trilha.py::test_log_do_banco_mostra_alteracao_fora_da_api` |
| `trg_set_updated_at` | Mantém o `updated_at` em 7 tabelas: `services`, `equipments` e as 5 de referência (`districts`, `technical_areas`, `unit_types`, `equipment_types`, `service_types`), conforme o catálogo do PostgreSQL (`pg_trigger`). Não está em `health_units`, cujo `updated_at` é do `trg_health_units_version` | `0011_09/06-14` | `test_ajustes_0011_09.py` |

## Etapa 6 · CRUD, interface e dashboard (spec 012, emenda funcional 2)
A interface é o front em HTML servido pelo próprio sistema (`frontend/app/`, spec 012), no mesmo domínio da API. Toda tela lê e grava pela API, que aplica permissões, escopo e auditoria; nenhum número da tela é fixo ou simulado. A matriz completa, requisito por requisito, está em [07-matriz-conformidade.md](07-matriz-conformidade.md), e o roteiro da apresentação em [08-roteiro-demonstracao.md](08-roteiro-demonstracao.md).

Os testes de interface (`tests/e2e_front/`, Playwright) rodam num compose descartável (`sgs-api-e2e-front-ui`), com dados criados pelo próprio teste; os de integração (`tests/integration/`), num PostgreSQL descartável (testcontainers).

### Tabelas com CRUD pela interface
| Tabela | Incluir | Consultar | Alterar | Excluir | Tela | Teste |
|---|---|---|---|---|---|---|
| `unit_types` | ✅ | ✅ | ✅ código, nome, área | **desativar e reativar** (exclusão lógica) | `#/referencias?tabela=tipos-unidade` | `test_referencias.py` |
| `equipment_types` | ✅ | ✅ | ✅ código (com `ON UPDATE CASCADE`), nome | **desativar e reativar** | `#/referencias?tabela=tipos-equipamento` | `test_referencias.py` |
| `service_types` | ✅ | ✅ | ✅ código, nome | **desativar e reativar** | `#/referencias?tabela=tipos-servico` | `test_referencias.py` |
| `services` | ✅ | ✅ | ✅ `PATCH` de nome, tipo, "no CNES" e situação | ✅ **física** (`DELETE`) | ficha › Serviços | `test_servicos.py` |
| `health_units` | ✅ `#/nova` | ✅ lista e ficha | ✅ ficha, com diff e `If-Match` | **desativar** pela procedure (exclusão lógica) | `#/unidades`, `#/unidade/{id}` | `test_lista.py`, `test_ficha.py`, `test_edicao.py`, `test_desativar.py` |

**Por que "excluir" é desativar nas referências e na unidade.** `health_units.unit_type_id` e `services.service_type_id` são chaves estrangeiras sem cascata na exclusão, e `equipments`/`services` apontam para a unidade com `ON DELETE RESTRICT`. Apagar um tipo ou uma unidade em uso falharia pela integridade referencial, e apagar a história contradiria o minimundo ("ela nunca é apagada, só desativada"). Por isso a API não tem rota de exclusão para eles, e a interface oferece desativar (e reativar, nas referências). Nenhuma FK foi alterada. A exclusão física pela interface existe só em `services`, para os quais nenhuma tabela aponta.

### Objetos da Etapa 5 na interface
| Objeto | Como aparece | Rota | Tela | Teste |
|---|---|---|---|---|
| `fn_normalize_name` | busca sem acento, caixa nem espaços | `GET /unidades?q=` | `#/unidades` (e busca do topo) | `test_lista.py::test_busca_sem_acento_caixa_nem_espacos_pela_fn_normalize_name` |
| `fn_registration_status` (IF/ELSIF) | situação cadastral: pizza, coluna e filtro | `GET /dashboard/inventario` | `#/qualidade` | `test_qualidade_historico.py::test_pizza_percentual_da_rede_e_tendencia_vem_da_api` |
| `sp_deactivate_unit` (atualização) | botão "Desativar unidade", com motivo | `POST /unidades/{id}/desativar` | ficha | `test_desativar.py` (+ `tests/integration/registry/test_sp_deactivate_unit.py`) |
| `sp_ensure_monthly_partitions` (CURSOR) | partições e linhas de cada uma (o procedimento roda pelo `sgs-admin banco particoes`) | `GET /auditoria/banco/particoes` | `#/historico?aba=particoes` | `test_qualidade_historico.py::test_particoes_criadas_pelo_procedimento` |
| `trg_registry_change_log` (log) | log do banco, com origem "pela API" ou "fora da API"; linha das alterações no período | `GET /auditoria/banco` | `#/historico?aba=banco`, `#/qualidade` | `test_qualidade_historico.py::test_log_do_banco_mostra_alteracao_feita_fora_da_api` |
| `trg_health_units_version` | "Versão N" e "Atualizado em" da unidade; 412 na edição concorrente | `ETag` de `GET`/`PATCH /unidades/{id}` | ficha | `test_ficha.py`, `test_edicao.py`, `test_desativar.py` |
| `trg_set_updated_at` | "Atualizado em" do serviço, antes e depois do `PATCH` | `PATCH /unidades/{id}/servicos/{sid}` | ficha › Serviços | `test_servicos.py::test_patch_muda_o_updated_at_pelo_trigger` |
| `audit_log_somente_insercao` | verificação da cadeia "íntegra" | `POST /auditoria/verificar` | `#/cadeia` (Auditor) | `test_qualidade_historico.py::test_auditor_ve_a_cadeia_integra` (+ `test_audit_immutable.py`) |
| `trg_roles_protect_system` | sem tela (não há edição de papéis) | — | — | `tests/integration/access/test_seed_matriz.py` |

### Consultas e views da Etapa 3 e 4 na interface
Todas estão na tela **Qualidade dos dados** (`#/qualidade`), lidas do catálogo `GET /dashboard/consultas`, com título, técnica SQL e justificativa vindos da API, resultado paginado e os filtros de distrito, tipo e área técnica (na URL). O histórico de uma unidade e o log do banco aparecem como links para as próprias telas.

| Consulta ou view | Técnica | Rota | Visualização | Teste |
|---|---|---|---|---|
| Unidades sem serviço | anti join | `/dashboard/consultas/unidades-sem-servico` | tabela | `test_qualidade_historico.py::test_totais_das_consultas_com_filtro_do_distrito_iguais_aos_da_api` |
| Conciliação unidade × equipamento | FULL OUTER JOIN | `/dashboard/consultas/conciliacao-unidade-equipamento` | tabela com a situação | idem |
| Distritos sem CNES acima da rede | subconsulta escalar no HAVING | `/dashboard/consultas/distritos-sem-cnes-acima-da-rede` | barras com a linha da rede | idem e `test_pizza_percentual_da_rede_e_tendencia_vem_da_api` |
| Unidades com serviço fora do CNES | EXISTS correlacionado | `/dashboard/consultas/unidades-com-servico-fora-do-cnes` | tabela | idem |
| Unidades por categoria | UNION ALL sobre a view | `/dashboard/consultas/unidades-por-categoria` | barras no Início e tabela | `test_inicio.py`, idem |
| Equipamentos por tipo e distrito | JOIN de 5 tabelas, GROUP BY, SUM | `/dashboard/consultas/equipamentos-por-tipo-e-distrito` | barras empilhadas | `test_graficos_sao_svg_acessiveis_com_os_dados_da_api` |
| Alterações por período | view, FILTER, IN | `/dashboard/consultas/alteracoes-por-periodo` | barras 7 × 30 dias e ritmo diário | idem e `test_pizza_percentual_da_rede_e_tendencia_vem_da_api` |
| Alterações recentes | view com 4 JOINs | `/dashboard/consultas/alteracoes-recentes` | Início e tabela | `test_inicio.py` |
| `vw_unit_inventory` | 3 INNER e 2 LEFT JOINs; `fn_registration_status` | `/dashboard/inventario` | tabela com filtro de situação, pizza e médias | `test_medias_somam_todas_as_paginas_do_inventario` |
| `vw_unit_history` | 3 INNER e 1 LEFT JOIN | `/unidades/{id}/historico` | linha do tempo da ficha, filtros de período e autor | `test_ficha.py::test_historico_da_view_em_ordem_com_filtros_de_periodo_e_autor` |

### Dashboard estatístico
Início (`#/inicio`) e Qualidade (`#/qualidade`), sempre com dados do PostgreSQL pela API e no escopo do usuário:
- **totais:** unidades, sem CNES, com pendência, alterações em 7 dias;
- **médias:** serviços e equipamentos por unidade, somando todas as páginas do inventário;
- **percentuais:** sem CNES na rede e por distrito (calculados pelo banco), situação cadastral;
- **tendência:** alterações por dia nos últimos 7 dias comparadas às dos últimos 30;
- **gráficos (SVG, sem biblioteca externa):** barras, barras agrupadas, barras empilhadas, pizza (rosca) e linha;
- **filtros:** distrito, tipo de unidade e área técnica (todas as consultas e gráficos); situação (inventário); período de 7 dias, 30 dias ou personalizado (linha das alterações, agregada por hora até 2 dias e por dia acima disso).
