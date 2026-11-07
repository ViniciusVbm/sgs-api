# 006 · Cadastro de unidades, equipamentos e serviços · Design

- Status: Aprovado (Rafael, 07/11/2026; aprovação só do dono pela exceção provisória de `steering/sdd-workflow.md`)

## Módulo
`modules/registry`. Usa `access` (require/scope_filter) e `audit` (registrar).

Os repositórios escrevem o SQL à mão com `text()` e parâmetros nomeados (ADR-0009). As tabelas continuam declaradas em `infrastructure/tables.py` para as migrações.

## Modelo
Migração `0006_registry` completa as tabelas de `docs/architecture/modelo-dados.md` §2: `districts`, `technical_areas`, `unit_types`, `equipment_types`, `service_types`, `health_units`, `equipments`, `services`. Acréscimos:
- `health_units.version` (int, default 1) para ETag/`If-Match` (R3.2). Quem incrementa é o trigger `trg_health_units_version` da spec 011 (R8), em toda escrita; o caso de uso **não** incrementa.
- `health_units.pending_issues` (int, default 0), mantido pela 007.
- `health_units.name_normalized` gerado por `fn_normalize_name(name)`, criada nesta migração (spec 011, R5): `unaccent` direto na coluna gerada falha, porque é STABLE. Índice único (`district_id`, `name_normalized`) (R1.4).
- FKs (spec 011, R9): `services.equipment_id → equipments(id) ON DELETE SET NULL`; `equipments.equipment_type_code → equipment_types(code) ON UPDATE CASCADE`; `equipments.unit_id` e `services.unit_id → health_units(id) ON DELETE RESTRICT`.
- Índice único parcial em `cnes WHERE cnes IS NOT NULL` (R1.3).
- Extensão `pg_trgm` + índice GIN em `name_normalized` para busca (R2.2, R2.7).

## Rotas
| Método e rota | Permissão | Requisitos |
|---|---|---|
| `GET /api/v1/unidades` | `unidade:read` + `scope_filter` | R2.1–R2.4, R2.6 |
| `POST /api/v1/unidades` | `unidade:create` (escopo pela área do tipo) | R1 |
| `GET /api/v1/unidades/{id}` | `unidade:read` | R2.5 |
| `PATCH /api/v1/unidades/{id}` | `unidade:update` + `If-Match` | R3 |
| `POST /api/v1/unidades/{id}/desativar` | `unidade:deactivate` | R4 |
| `GET/POST /api/v1/unidades/{id}/equipamentos` · `PATCH/DELETE .../{eid}` | `unidade:read` / `equipamento:write` | R5.1, R5.3 |
| `GET/POST /api/v1/equipamentos` (sem unidade) | `equipamento:write` global | R5.2 |
| `GET/POST /api/v1/unidades/{id}/servicos` · `PATCH/DELETE .../{sid}` | `unidade:read` / `servico:write` | R6.1, R6.3 |
| `GET/POST /api/v1/servicos` (soltos) | `servico:write` global | R6.2 |
| `GET /api/v1/referencias/*` | autenticado | R7.1 |
| `POST/PATCH /api/v1/referencias/*` | `regra_validacao:manage` | R7.2 |

## Schemas
- `UnidadeCreate`, `UnidadeUpdate` (todos opcionais), `UnidadeOut`, `UnidadeDetalheOut` (com `equipamentos[]`, `servicos[]`), `PaginaOut[T]` (`itens`, `total`, `pagina`, `tamanho`).
- Validação de formato fica nos schemas; regras de negócio na spec 007.

## Campos estruturais (R3.4)
Constante no domínio: `CAMPOS_ESTRUTURAIS = {"district_id", "unit_type_id", "cnes"}`. Para alterá-los, o caso de uso exige `unidade:update` com escopo `global` ou `area`; com escopo `distrito`/`unidade` responde 403 apontando os campos.

## Diff e auditoria
Função pura `diff(antes: dict, depois: dict) -> list[Mudanca]` no domínio; o caso de uso grava a unidade com `UPDATE ... WHERE id = :id AND version = :esperada RETURNING version` (nenhuma linha → 412) e chama `audit.registrar("unidade.atualizada", ...)` na mesma transação (R3.5, R3.6). Mudanças em equipamento/serviço geram `unidade.equipamento_*` / `unidade.servico_*` com `entity_type = 'unidade'` e `entity_id` da unidade (R5.3), para aparecerem na `vw_unit_history` da 011.

## Desativação (R4)
O caso de uso chama `CALL sp_deactivate_unit(...)` da spec 011 (R6): unidade inexistente → 404; já inativa → 200 sem auditoria; senão audita `unidade.desativada` com o motivo nos metadados.

## Busca
`ILIKE` sobre `name_normalized` com `fn_normalize_name(:q)` (spec 011, R5.2) + `similarity` para ordenar quando há `q`. Paginação offset (volume ~250–1.000 unidades não justifica cursor).

## Estratégia de testes
- Unidade: normalização de nome, diff, regra de campos estruturais.
- Integração: criação completa; 409 por CNES e por nome; filtros combinados; escopo (gestor da unidade A → 403 na B); `If-Match` desatualizado → 412; PATCH sem mudança não audita; renomear unidade reflete em serviços.
- Desempenho: teste `slow` com 1.000 unidades verificando p95 < 3 s na busca.
