-- Objetivo: contar os equipamentos de um tipo, pelo código.
-- Justificativa: `referencia.atualizada` registra quantos equipamentos a correção do código
--   alcançou pela cascata (006/R7.3, 011/R9.2).
-- Uso: PATCH /api/v1/referencias/tipos-equipamento/{id} (011/T18).
-- Requisitos: 006/R7.3, 011/R9.2
SELECT count(*) FROM equipments WHERE equipment_type_code = :code
