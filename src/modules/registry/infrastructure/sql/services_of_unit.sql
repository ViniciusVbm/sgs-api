-- Objetivo: listar os serviços de uma unidade, ou os soltos.
-- Justificativa: 006/R6.1 e R6.2. Com `unit_id` nulo, só os soltos; senão, os da unidade, por
--   `ix_services_unit_id` (011/R1.2).
-- Uso: GET /api/v1/unidades/{id}/servicos, GET /api/v1/servicos, detalhe da unidade.
-- Requisitos: 006/R2.5, 006/R6.1, 006/R6.2, 011/R1.2
SELECT id, unit_id, equipment_id, service_type_id, name, in_cnes, status, created_at, updated_at
FROM services
WHERE (CAST(:unit_id AS uuid) IS NULL AND unit_id IS NULL)
   OR unit_id = CAST(:unit_id AS uuid)
ORDER BY name, id
