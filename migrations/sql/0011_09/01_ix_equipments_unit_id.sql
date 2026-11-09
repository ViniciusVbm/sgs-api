-- Objetivo: índice dos equipamentos de uma unidade.
-- Justificativa: `equipments.unit_id` é FK com ON DELETE RESTRICT para `health_units`; sem índice,
--   cada tentativa de excluir unidade varre `equipments` inteira para conferir a restrição. A
--   `vw_unit_inventory` (contagem por unidade), a conciliação unidade x equipamento (full outer
--   join) e a listagem `GET /unidades/{id}/equipamentos` procuram os equipamentos pela unidade.
-- Uso: `vw_unit_inventory`; `unit_equipment_reconciliation.sql`; rotas de equipamentos da 006/T7.
-- Requisitos: 011/T21 (emenda de 09/11/2026); 011/R9.3
CREATE INDEX ix_equipments_unit_id ON equipments (unit_id);
