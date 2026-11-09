-- Objetivo: listar o log do banco, paginado e filtrado.
-- Justificativa: o `trg_registry_change_log` (011/R7) grava toda escrita no cadastro, inclusive as
--   feitas fora da API; o Auditor precisa ver, por exemplo, o que mudou direto no banco
--   (`fora_da_api`). O nome do gestor já chega mascarado pelo trigger (LGPD).
--   - Filtros: período (poda as partições mensais), tabela e só fora da API.
-- Uso: GET /api/v1/auditoria/banco (011/T15). O período usa `ix_db_change_log_occurred_at`.
-- Requisitos: 011/R7.7, 011/R7.8
SELECT
    id,
    occurred_at,
    table_name,
    operation,
    row_id,
    changed_columns,
    db_user,
    via_api,
    count(*) OVER () AS total
FROM db_change_log
WHERE (CAST(:de AS timestamptz) IS NULL OR occurred_at >= CAST(:de AS timestamptz))
  AND (CAST(:ate AS timestamptz) IS NULL OR occurred_at < CAST(:ate AS timestamptz))
  AND (CAST(:tabela AS text) IS NULL OR table_name = CAST(:tabela AS text))
  AND (NOT CAST(:fora_da_api AS boolean) OR NOT via_api)
ORDER BY occurred_at DESC, id DESC
LIMIT :limit OFFSET :offset
