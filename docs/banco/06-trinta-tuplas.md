# 30 tuplas por tabela (decisão D1)

Medido depois de `sgs-admin seed demo` (`tests/integration/tools/test_seed_demo.py`) e depois de `build/sql-bd-insercao.sql` (`tests/integration/tools/test_sql_bd.py`).

| Tabela | Linhas | Situação |
|---|---|---|
| `health_units` | 37 | ✅ 27 unidades da `feat/003` (as do Recife) + 10 de Saúde Mental |
| `equipments` | 31 | ✅ |
| `services` | 35 | ✅ |
| `users` | 30 | ✅ pessoas fictícias, todos os papéis |
| `role_assignments` | 30 | ✅ todos os escopos |
| `audit_log` | 138 | ✅ gerado pelo seed (um evento por registro criado) |
| `db_change_log` | 103 | ✅ gerado pelo trigger (inserções no cadastro) |
| `sessions`, `refresh_tokens` | conforme o uso | gerados pelo login; não há seed (seriam credenciais) |
| `districts` | 8 | **domínio fechado**: os 8 distritos sanitários do Recife |
| `technical_areas` | 4 | **domínio fechado**: as áreas técnicas da Secretaria |
| `unit_types` | 10 | referência real da rede (7 da 0006 + UPA, Hospital, Laboratório) |
| `equipment_types` | 5 | referência real (3 da 0006 + Academia da Saúde, Base do SAMU) |
| `service_types` | 4 | referência da 0006 |
| `roles` | 7 | **domínio fechado**: os papéis da arquitetura |
| `permissions` | 17 | **domínio fechado**: as permissões da matriz |
| `role_permissions` | 51 | matriz |
| `group_role_mappings` | 0 | depende da integração com diretório (spec 004, não implementada) |

**Justificativa.** Pela decisão D1, as tabelas de domínio fechado ficam com a quantidade real. Inventar distritos, áreas, papéis ou permissões quebraria o modelo (um 9º distrito não existe; um papel inventado entraria na matriz de acesso). Se a exigência for estrita para toda tabela, a saída é pedir ao professor que aceite a justificativa; o grupo deve confirmar.

**Unidades descartadas da `feat/003`:** "UPA Barra do Ceara" (Fortaleza), "UBS Muribeca" (Jaboatão) e "UBS Nossa Senhora do Ó" (fora do Recife). A lista está em `seeds/demo/unidades.json` (`descartadas_da_003`). Os "equipamentos" da 003 (monitor, ventilador, tomógrafo) são aparelhos médicos, não equipamentos de saúde no sentido do domínio (`steering/product.md`), e não foram importados. O mapeamento de bairro para distrito sanitário no seed é aproximado e serve só para demonstração.
