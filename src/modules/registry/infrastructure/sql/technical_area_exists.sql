-- Objetivo: conferir se a área técnica existe.
-- Justificativa: tipo de unidade novo ou alterado precisa de área existente (422).
-- Uso: referências (006/T9).
-- Requisitos: 006/R7.2
SELECT EXISTS (SELECT 1 FROM technical_areas WHERE id = :id)
