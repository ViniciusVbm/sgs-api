-- Objetivo: aplicar os campos enviados num PATCH de serviço.
-- Justificativa: atualização parcial com texto fixo (ADR-0009); `updated_at` pelo trigger.
-- Uso: PATCH /api/v1/unidades/{id}/servicos/{sid} e PATCH /api/v1/servicos/{sid} (006/T8).
-- Requisitos: 006/R6.1, 006/R6.2, 006/R6.3
UPDATE services
SET
    equipment_id = CASE WHEN :set_equipment_id THEN :equipment_id ELSE equipment_id END,
    service_type_id = CASE WHEN :set_service_type_id THEN :service_type_id ELSE service_type_id END,
    name = CASE WHEN :set_name THEN :name ELSE name END,
    in_cnes = CASE WHEN :set_in_cnes THEN :in_cnes ELSE in_cnes END,
    status = CASE WHEN :set_status THEN :status ELSE status END
WHERE id = :id
RETURNING id, unit_id, equipment_id, service_type_id, name, in_cnes, status, created_at, updated_at
