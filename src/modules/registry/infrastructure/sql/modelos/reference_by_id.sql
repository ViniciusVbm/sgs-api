-- Objetivo: ler um item de referência pelo id.
-- Justificativa: a alteração compara antes e depois e audita (006/R7.2). Ver `reference_list.sql`
--   sobre `{tabela}` e `{area}`.
-- Uso: PATCH /api/v1/referencias/{tipo}/{id} (006/T9).
-- Requisitos: 006/R7.2
SELECT id, code, name, is_active, {area} AS technical_area_id
FROM {tabela}
WHERE id = :id
