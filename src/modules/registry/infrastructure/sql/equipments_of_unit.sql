-- Objetivo: listar os equipamentos de uma unidade, ou os sem unidade.
-- Justificativa: 006/R5.1 (equipamentos da unidade) e R5.2 (sem unidade, como a UTI móvel). Com
--   `unit_id` pedido nulo, só os de `unit_id` nulo; senão, os da unidade, por `ix_equipments_unit_id`.
-- Uso: GET /api/v1/unidades/{id}/equipamentos, GET /api/v1/equipamentos, detalhe da unidade.
-- Requisitos: 006/R2.5, 006/R5.1, 006/R5.2
SELECT id, unit_id, cnes, name, equipment_type_code, quantity, status, created_at, updated_at
FROM equipments
WHERE (CAST(:unit_id AS uuid) IS NULL AND unit_id IS NULL)
   OR unit_id = CAST(:unit_id AS uuid)
ORDER BY name, id
