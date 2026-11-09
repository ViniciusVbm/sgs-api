-- Objetivo: alterar código, nome ou situação de um item de referência.
-- Justificativa: 006/R7.2. Corrigir o código de um tipo de equipamento chega a todos os
--   equipamentos dele pela FK com ON UPDATE CASCADE (006/R7.3, 011/R9.2). Ver
--   `reference_list.sql` sobre `{tabela}` e `{area}`.
-- Uso: PATCH /api/v1/referencias/{tipo}/{id} (006/T9, 011/T18).
-- Requisitos: 006/R7.2, 006/R7.3, 011/R9.2
UPDATE {tabela}
SET
    code = CASE WHEN :set_code THEN :code ELSE code END,
    name = CASE WHEN :set_name THEN :name ELSE name END,
    is_active = CASE WHEN :set_is_active THEN :is_active ELSE is_active END
WHERE id = :id
RETURNING id, code, name, is_active, {area} AS technical_area_id
