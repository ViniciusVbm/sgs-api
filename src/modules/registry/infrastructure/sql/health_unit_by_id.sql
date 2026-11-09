-- Objetivo: ler uma unidade pelo id.
-- Justificativa: detalhe (006/R2.5) e ponto de partida do PATCH, que compara antes e depois.
-- Uso: GET /api/v1/unidades/{id}; casos de uso de atualização e desativação (006/T4 a T6).
-- Requisitos: 006/R2.5, 006/R3.1
SELECT
    id, name, cnes, unit_type_id, district_id, cep, address, neighborhood, phone,
    manager_name, opening_hours, latitude, longitude, status,
    pending_issues, version, created_at, updated_at
FROM health_units
WHERE id = :id
