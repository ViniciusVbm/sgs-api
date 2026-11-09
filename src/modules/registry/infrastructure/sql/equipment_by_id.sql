-- Objetivo: ler um equipamento pelo id.
-- Justificativa: alteração e remoção conferem a que unidade o equipamento pertence (R5.1).
-- Uso: rotas de equipamento (006/T7).
-- Requisitos: 006/R5.1, 006/R5.2
SELECT id, unit_id, cnes, name, equipment_type_code, quantity, status, created_at, updated_at
FROM equipments
WHERE id = :id
