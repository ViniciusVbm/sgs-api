-- Objetivo: domínio do status do serviço.
-- Justificativa: como o do equipamento, fixado na 006/T8: `ativo` ou `inativo`.
-- Uso: escrita de serviços (006/T8).
-- Requisitos: 011/T21; 006/R6
ALTER TABLE services
    ADD CONSTRAINT ck_services_status_valido CHECK (status IN ('ativo', 'inativo'));
