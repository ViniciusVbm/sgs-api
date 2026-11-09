-- Objetivo: contar os serviços ligados a um equipamento.
-- Justificativa: remover o equipamento põe `services.equipment_id` em nulo (ON DELETE SET NULL,
--   011/R9.1); a auditoria registra quantos serviços perderam o vínculo.
-- Uso: remoção de equipamento (006/T7). Usa `ix_services_equipment_id` (011/T21).
-- Requisitos: 006/R5.3, 011/R9.1
SELECT count(*) FROM services WHERE equipment_id = :id
