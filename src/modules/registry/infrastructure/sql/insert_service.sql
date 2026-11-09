-- Objetivo: gravar um serviço novo, de uma unidade ou solto.
-- Justificativa: 006/R6.1 a R6.3; o vínculo com a unidade e o equipamento é pelo id (R6.4).
-- Uso: POST /api/v1/unidades/{id}/servicos e POST /api/v1/servicos (006/T8).
-- Requisitos: 006/R6.1, 006/R6.2, 006/R6.3, 006/R6.4
INSERT INTO services (id, unit_id, equipment_id, service_type_id, name, in_cnes, status)
VALUES (:id, :unit_id, :equipment_id, :service_type_id, :name, :in_cnes, :status)
RETURNING id, unit_id, equipment_id, service_type_id, name, in_cnes, status, created_at, updated_at
