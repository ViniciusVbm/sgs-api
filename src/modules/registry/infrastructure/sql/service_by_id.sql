-- Objetivo: ler um serviço pelo id.
-- Justificativa: alteração e remoção conferem a que unidade o serviço pertence (R6.1).
-- Uso: rotas de serviço (006/T8).
-- Requisitos: 006/R6.1, 006/R6.2
SELECT id, unit_id, equipment_id, service_type_id, name, in_cnes, status, created_at, updated_at
FROM services
WHERE id = :id
