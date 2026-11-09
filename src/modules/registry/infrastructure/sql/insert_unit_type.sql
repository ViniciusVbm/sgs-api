-- Objetivo: incluir um tipo de unidade, com a sua área técnica.
-- Justificativa: 006/R7.2; o tipo de unidade é a única referência com área (escopo da 003).
-- Uso: POST /api/v1/referencias/tipos-unidade (006/T9).
-- Requisitos: 006/R7.2
INSERT INTO unit_types (code, name, technical_area_id)
VALUES (:code, :name, :technical_area_id)
ON CONFLICT DO NOTHING
RETURNING id, code, name, is_active, technical_area_id
