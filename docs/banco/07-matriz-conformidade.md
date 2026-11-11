# Matriz de conformidade · Etapas 03 a 06

Cada requisito do enunciado aponta o objeto no banco, a rota da API, a tela e o teste que o prova. Situação conferida em 10/11/2026 na branch `feat/012-etapa06`.

**Onde rodam os testes:**
- `tests/e2e_front/` (Playwright): num compose descartável (`sgs-api-e2e-front-ui`), com dados criados pelo próprio teste;
- `tests/integration/`: num PostgreSQL descartável (testcontainers).

As telas abrem em `https://<host>/` (ver [08-roteiro-demonstracao.md](08-roteiro-demonstracao.md)). Os objetos e suas justificativas estão em [05-objetos-e-justificativas.md](05-objetos-e-justificativas.md).

## Etapa 03 · Consultas e interface
| Requisito | Objeto no banco | Rota | Tela | Teste |
|---|---|---|---|---|
| 4 ou mais consultas | 8 consultas: 4 da Etapa 3 (por categoria, equipamentos por tipo e distrito, alterações por período, alterações recentes) e 4 da Etapa 4. O catálogo tem 13 entradas: essas 8, as 2 views (inventário e histórico da unidade), o resumo e as 2 visões de auditoria (log do banco e partições) | `GET /dashboard/consultas` e `/dashboard/consultas/*` | `#/qualidade` | `test_qualidade_historico.py::test_catalogo_inteiro_com_titulo_tecnica_e_justificativa` |
| Consulta com JOIN | `equipments_by_type_district.sql` (5 tabelas), `recent_changes.sql` (view com 4 JOINs) | `/dashboard/consultas/equipamentos-por-tipo-e-distrito`, `/alteracoes-recentes` | `#/qualidade`, `#/inicio` | `test_graficos_sao_svg_acessiveis_com_os_dados_da_api`, `test_inicio.py` |
| SQL explícito executado pelo backend | `src/modules/*/infrastructure/sql/*.sql` (ADR-0009) | todas | todas | `tests/architecture/test_sql_documentado.py` |
| CRUD de 2 tabelas ou mais | ver Etapa 06 (5 tabelas) | — | — | — |
| Visualização dos resultados | tabelas paginadas de cada consulta | `/dashboard/consultas/*` | `#/qualidade` | `test_totais_das_consultas_com_filtro_do_distrito_iguais_aos_da_api` |
| Gráficos e indicadores | consultas agregadas | `/dashboard/resumo`, `/dashboard/consultas/*` | `#/inicio`, `#/qualidade` | `test_inicio.py`, `test_graficos_sao_svg_acessiveis_com_os_dados_da_api` |

## Etapa 04 · Consultas avançadas, views e índices
| Requisito | Objeto no banco | Rota | Tela | Teste |
|---|---|---|---|---|
| ANTI JOIN | `units_without_services.sql` | `/dashboard/consultas/unidades-sem-servico` | `#/qualidade` | `test_totais_das_consultas_com_filtro_do_distrito_iguais_aos_da_api`; `tests/integration/dashboard/test_consultas_qualidade.py` |
| FULL OUTER JOIN | `unit_equipment_reconciliation.sql` | `/dashboard/consultas/conciliacao-unidade-equipamento` | `#/qualidade` | idem |
| Subconsulta (1) | `districts_cnes_above_network.sql` (escalar no HAVING) | `/dashboard/consultas/distritos-sem-cnes-acima-da-rede` | `#/qualidade` (gráfico com a linha da rede) | `test_pizza_percentual_da_rede_e_tendencia_vem_da_api`; `test_painel.py` |
| Subconsulta (2) | `units_with_services_outside_cnes.sql` (EXISTS correlacionado) | `/dashboard/consultas/unidades-com-servico-fora-do-cnes` | `#/qualidade` | `test_totais_das_consultas_…`; `test_painel.py` |
| View 1 | `vw_unit_inventory` | `/dashboard/inventario` | `#/qualidade` (inventário, pizza, médias) | `test_medias_somam_todas_as_paginas_do_inventario`; `tests/integration/db/test_views.py` |
| View 2 | `vw_unit_history` | `/unidades/{id}/historico` | ficha › Histórico | `test_ficha.py::test_historico_da_view_em_ordem_com_filtros_de_periodo_e_autor`; `test_views.py` |
| 2 índices adicionais ou mais | `ix_audit_log_entity`, `ix_services_unit_id`, `ix_equipments_unit_id`, `ix_health_units_name_normalized_trgm`, `ix_services_equipment_id`, `ix_db_change_log_occurred_at` | usados pelo histórico, pelas consultas e pela busca | ficha, `#/qualidade`, `#/unidades` | `tests/integration/db/test_indices.py` (EXPLAIN com 1.000 unidades; [planos-indices.txt](planos-indices.txt)) |

## Etapa 05 · Funções, procedimentos e triggers
| Requisito | Objeto no banco | Rota | Tela | Teste |
|---|---|---|---|---|
| Função 1 | `fn_normalize_name` | `GET /unidades?q=` | `#/unidades` (busca) | `test_lista.py::test_busca_sem_acento_caixa_nem_espacos_pela_fn_normalize_name`; `test_normalizacao.py` |
| Função 2, com estrutura condicional | `fn_registration_status` (IF/ELSIF) | `/dashboard/inventario` | `#/qualidade` (pizza e coluna "situação cadastral") | `test_pizza_percentual_da_rede_e_tendencia_vem_da_api`; `test_situacao_cadastral.py` |
| Procedimento de atualização | `sp_deactivate_unit` | `POST /unidades/{id}/desativar` | ficha (botão "Desativar unidade") | `test_desativar.py`; `test_sp_deactivate_unit.py` |
| Procedimento com CURSOR | `sp_ensure_monthly_partitions` | efeito em `GET /auditoria/banco/particoes` | `#/historico?aba=particoes` | `test_particoes_criadas_pelo_procedimento`; `tests/integration/audit/test_particoes.py` |
| Trigger que grava log | `trg_registry_change_log` → `db_change_log` | `/auditoria/banco` | `#/historico?aba=banco` | `test_log_do_banco_mostra_alteracao_feita_fora_da_api`; `test_log_banco.py` |
| Trigger 2 | `trg_health_units_version` (versão e `updated_at` da unidade) | `ETag` de `/unidades/{id}` | ficha (versão, data, 412) | `test_edicao.py::test_edicao_com_diff_if_match_versao_e_updated_at`, `test_dois_navegadores_…412…`; `test_versao_trigger.py` |
| Trigger 3 | `trg_set_updated_at`: `updated_at` em 7 tabelas: `services`, `equipments` e as 5 de referência (`districts`, `technical_areas`, `unit_types`, `equipment_types`, `service_types`); não está em `health_units` | `PATCH /unidades/{id}/servicos/{sid}` | ficha › Serviços | `test_servicos.py::test_patch_muda_o_updated_at_pelo_trigger`; `test_ajustes_0011_09.py` |
| Triggers da auditoria | `audit_log_somente_insercao`, `trg_roles_protect_system`; `db_change_log_somente_insercao` e `ENABLE ALWAYS` (0013_03) | `POST /auditoria/verificar` (cabeça e âncora, spec 013) | `#/cadeia` | `test_auditor_ve_a_cadeia_integra`, `test_cadeia_mostra_cabeca_cadeia_e_ancora`; `test_audit_immutable.py`, `test_log_banco_privilegios.py`, `test_adulteracao.py` |
| Restauração preservando constraints e triggers | `pg_dump -Fc` / `pg_restore`; `ck_audit_log_origem_obrigatoria` NOT VALID; triggers `ENABLE ALWAYS` | `sgs-admin auditoria verificar --ancora` | — | `test_backup_restauracao.py` (evidência em `docs/operacao/evidencias/`) |

## Etapa 06 · Integração final
| Requisito | Objeto no banco | Rota | Tela | Teste |
|---|---|---|---|---|
| CRUD de 4 tabelas ou mais | `unit_types`, `equipment_types`, `service_types`, `services`, `health_units` | `/referencias/{tipo}`, `/unidades/{id}/servicos`, `/unidades` | `#/referencias`, ficha, `#/nova` | `test_referencias.py`, `test_servicos.py`, `test_edicao.py`, `test_desativar.py` |
| Funções e procedimentos pela interface | busca, situação cadastral, desativação, partições | ver Etapa 05 | ver Etapa 05 | ver Etapa 05 |
| Efeito dos triggers | log, versão, `updated_at`, cadeia | ver Etapa 05 | `#/historico`, ficha, `#/cadeia` | ver Etapa 05 |
| `ON UPDATE CASCADE` visível | FK `equipments.equipment_type_code` | `PATCH /referencias/tipos-equipamento/{id}` | `#/referencias?tabela=tipos-equipamento` | `test_referencias.py::test_trocar_o_codigo_do_tipo_de_equipamento_cascateia_nos_equipamentos` |
| Consultas e views acessíveis, com filtros | ver Etapas 03 e 04 | `/dashboard/consultas/*?distrito&tipo&area` | `#/qualidade` | `test_totais_das_consultas_com_filtro_do_distrito_iguais_aos_da_api` |
| Dashboard com dados reais | consultas e views | `/dashboard/*`, `/auditoria/banco` | `#/inicio`, `#/qualidade` | `test_inicio.py`, `test_qualidade_historico.py` |
| Totais, médias, percentuais, tendências | resumo, inventário, distritos sem CNES, alterações por período | idem | `#/qualidade` (indicadores) | `test_medias_somam_todas_as_paginas_do_inventario`, `test_pizza_percentual_da_rede_e_tendencia_vem_da_api` |
| Gráficos (barras, pizza, linha) e filtros interativos | idem | idem | `#/qualidade` | `test_graficos_sao_svg_acessiveis_com_os_dados_da_api`, `test_linha_do_periodo_soma_todas_as_paginas_e_preenche_zeros` |
| Permissões e escopos na interface | matriz RBAC (spec 003) | `GET /me` | menu e botões por papel | `test_perfis.py` e os casos de papel de cada arquivo acima |
| README e instruções | — | — | — | [README.md](../../README.md) § Demonstração da interface; [08-roteiro-demonstracao.md](08-roteiro-demonstracao.md) |

## Limitações conhecidas
- **Dados de um único dia:** o seed grava todo o histórico num único dia. A linha das alterações mostra o aviso de histórico insuficiente até haver uso em outros dias; as ações feitas na demonstração viram pontos novos (o período "Personalizado" de hoje agrupa por hora).
- **Exclusão nas referências e na unidade:** é desativação (exclusão lógica), pela integridade referencial (ver 05 § Etapa 6). A exclusão física pela interface existe só em `services`.
- **`ON DELETE SET NULL`** (`services.equipment_id`): a remoção de equipamentos não tem tela, porque a aba de aparelhos depende da DF1 (spec 012, R9.1). A prova é o teste de integração `tests/integration/registry/test_integridade.py`.
- **30 tuplas:** cenário D **aprovado** (aprovação formal do professor comunicada pelo responsável pelo projeto; o documento não está anexado ao repositório). As tabelas de negócio e de auditoria têm 30 ou mais; as de domínio fechado, uso e infraestrutura ficam com a quantidade real, com a justificativa de [06-trinta-tuplas.md](06-trinta-tuplas.md). Nenhuma tupla artificial foi inserida.
- **Fora da API:** o teste prova a origem "fora da API" com um `UPDATE` direto no banco descartável do E2E. No banco da demonstração, essa linha só aparece se alguém alterar o banco por fora, o que o roteiro não faz.
