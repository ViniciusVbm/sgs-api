-- Objetivo: conferir se há área técnica com o id do filtro.
-- Justificativa: o filtro de área do resumo (009/R1.6) responde 422 quando aponta uma área que não
--   existe, como os de distrito e tipo (011/R2.9). Lê só a referência, sem escopo.
-- Uso: validação de filtros do dashboard.
-- Requisitos: 009/R1.6, 011/R2.9
SELECT EXISTS (SELECT 1 FROM technical_areas WHERE id = :technical_area_id)
