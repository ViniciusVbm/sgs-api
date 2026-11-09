-- Objetivo: apagar um equipamento.
-- Justificativa: equipamentos têm exclusão física (decisão U5 da 011); os serviços ligados a ele
--   ficam, com o vínculo em nulo (ON DELETE SET NULL, 011/R9.1).
-- Uso: DELETE /api/v1/unidades/{id}/equipamentos/{eid} e DELETE /api/v1/equipamentos/{eid}.
-- Requisitos: 006/R5.1, 011/R9.1
DELETE FROM equipments WHERE id = :id
