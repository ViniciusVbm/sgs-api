-- Objetivo: conferir se o tipo de equipamento existe e está ativo.
-- Justificativa: equipamento novo ou alterado só aceita tipo ativo (422 apontando o campo).
-- Uso: escrita de equipamentos (006/T7).
-- Requisitos: 006/R5.1, 006/R7.2
SELECT EXISTS (SELECT 1 FROM equipment_types WHERE code = :code AND is_active)
