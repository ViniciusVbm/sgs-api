-- Objetivo: conferir se o tipo de serviço existe e está ativo.
-- Justificativa: serviço novo ou alterado só aceita tipo ativo (422 apontando o campo).
-- Uso: escrita de serviços (006/T8).
-- Requisitos: 006/R6.1, 006/R7.2
SELECT EXISTS (SELECT 1 FROM service_types WHERE id = :id AND is_active)
