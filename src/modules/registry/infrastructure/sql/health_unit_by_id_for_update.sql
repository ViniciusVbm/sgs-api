-- Objetivo: ler uma unidade pelo id travando a linha até o fim da transação.
-- Justificativa: o PATCH compara o estado atual com o pedido e grava; a trava impede outra
--   transação de alterar a unidade no meio (o `If-Match` cobre o intervalo entre as requisições).
-- Uso: caso de uso de atualização (006/T5).
-- Requisitos: 006/R3.1, 006/R3.2
SELECT
    id, name, cnes, unit_type_id, district_id, cep, address, neighborhood, phone,
    manager_name, opening_hours, latitude, longitude, status,
    pending_issues, version, created_at, updated_at
FROM health_units
WHERE id = :id
FOR UPDATE
