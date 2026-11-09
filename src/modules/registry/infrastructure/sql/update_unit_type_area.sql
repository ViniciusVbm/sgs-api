-- Objetivo: mudar a área técnica de um tipo de unidade.
-- Justificativa: 006/R7.2. Muda o escopo de área de todas as unidades do tipo (spec 003).
-- Uso: PATCH /api/v1/referencias/tipos-unidade/{id} com `area_tecnica_id` (006/T9).
-- Requisitos: 006/R7.2
UPDATE unit_types SET technical_area_id = :technical_area_id WHERE id = :id
