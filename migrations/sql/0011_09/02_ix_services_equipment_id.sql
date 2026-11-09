-- Objetivo: índice dos serviços ligados a um equipamento.
-- Justificativa: `services.equipment_id` é FK com ON DELETE SET NULL; ao remover um equipamento,
--   o PostgreSQL procura os serviços dele para pôr o vínculo em nulo. Sem índice, cada remoção
--   varre `services` inteira.
-- Uso: DELETE /unidades/{id}/equipamentos/{eid} e DELETE /equipamentos/{eid} (006/T7).
-- Requisitos: 011/T21 (emenda de 09/11/2026); 011/R9.1
CREATE INDEX ix_services_equipment_id ON services (equipment_id);
