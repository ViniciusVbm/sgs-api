-- Objetivo: apagar um serviço.
-- Justificativa: serviços têm exclusão física (decisão U5 da 011).
-- Uso: DELETE /api/v1/unidades/{id}/servicos/{sid} e DELETE /api/v1/servicos/{sid} (006/T8).
-- Requisitos: 006/R6.1
DELETE FROM services WHERE id = :id
