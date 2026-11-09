-- Objetivo: aplicar os campos enviados num PATCH de equipamento.
-- Justificativa: atualização parcial com texto fixo; cada coluna só muda com o seu
--   `set_<coluna>` verdadeiro (ADR-0009). `updated_at` vem do `trg_set_updated_at` (011/T21).
-- Uso: PATCH /api/v1/unidades/{id}/equipamentos/{eid} e PATCH /api/v1/equipamentos/{eid}.
-- Requisitos: 006/R5.1, 006/R5.2
UPDATE equipments
SET
    cnes = CASE WHEN :set_cnes THEN :cnes ELSE cnes END,
    name = CASE WHEN :set_name THEN :name ELSE name END,
    equipment_type_code = CASE WHEN :set_equipment_type_code THEN :equipment_type_code ELSE equipment_type_code END,
    quantity = CASE WHEN :set_quantity THEN :quantity ELSE quantity END,
    status = CASE WHEN :set_status THEN :status ELSE status END
WHERE id = :id
RETURNING id, unit_id, cnes, name, equipment_type_code, quantity, status, created_at, updated_at
