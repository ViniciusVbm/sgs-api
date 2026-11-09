-- Objetivo: domínio do status do equipamento.
-- Justificativa: a 0006 deixou `equipments.status` sem CHECK até os valores serem fixados
--   (pergunta em aberto da 006). A 006/T7 os fixa: `ativo`, `inativo`, `em_manutencao`.
-- Uso: escrita de equipamentos (006/T7).
-- Requisitos: 011/T21; 006/R5
ALTER TABLE equipments
    ADD CONSTRAINT ck_equipments_status_valido
    CHECK (status IN ('ativo', 'inativo', 'em_manutencao'));
