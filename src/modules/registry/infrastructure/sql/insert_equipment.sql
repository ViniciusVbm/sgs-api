-- Objetivo: gravar um equipamento novo, de uma unidade ou sem unidade.
-- Justificativa: 006/R5.1 e R5.2. O tipo vem pelo código, FK com ON UPDATE CASCADE (011/R9.2).
-- Uso: POST /api/v1/unidades/{id}/equipamentos e POST /api/v1/equipamentos (006/T7).
-- Requisitos: 006/R5.1, 006/R5.2
INSERT INTO equipments (id, unit_id, cnes, name, equipment_type_code, quantity, status)
VALUES (:id, :unit_id, :cnes, :name, :equipment_type_code, :quantity, :status)
RETURNING id, unit_id, cnes, name, equipment_type_code, quantity, status, created_at, updated_at
