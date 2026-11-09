-- Objetivo: quantidade de equipamento positiva.
-- Justificativa: um equipamento cadastrado existe ao menos uma vez; zero ou negativo é erro de
--   digitação, que o banco recusa mesmo se a aplicação falhar.
-- Uso: escrita de equipamentos (006/T7).
-- Requisitos: 011/T21; 006/R5
ALTER TABLE equipments
    ADD CONSTRAINT ck_equipments_quantity_positiva CHECK (quantity > 0);
