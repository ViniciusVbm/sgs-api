-- Objetivo: quantidade de equipamentos por tipo de equipamento e distrito.
-- Justificativa: segunda consulta da Etapa 03 da `feat/003-interface-dashboard`
--   (`equipamentos_por_tipo_e_distrito`), reescrita para o esquema da 006. Mostra como os
--   equipamentos de saúde se distribuem na rede (009/R2.2).
--   - JOIN de cinco tabelas: equipamento, tipo de equipamento, unidade, tipo de unidade (para a
--     área técnica do escopo) e distrito.
--   - Soma `quantity`, porque uma linha pode representar vários equipamentos iguais.
--   - Equipamento sem unidade não tem distrito e fica de fora (aparece na conciliação).
-- Uso: GET /api/v1/dashboard/consultas/equipamentos-por-tipo-e-distrito (009/T4).
-- Requisitos: 009/R2.2, 009/R2.5
WITH units AS (
    SELECT
        hu.id AS unit_id,
        hu.district_id,
        hu.unit_type_id,
        t.technical_area_id,
        d.name AS district_name
    FROM health_units AS hu
    JOIN unit_types AS t ON t.id = hu.unit_type_id
    JOIN districts AS d ON d.id = hu.district_id
)
SELECT
    et.code AS equipment_type_code,
    et.name AS equipment_type_name,
    u.district_id,
    u.district_name,
    count(*) AS equipment_count,
    sum(e.quantity) AS total_quantity
FROM equipments AS e
JOIN equipment_types AS et ON et.code = e.equipment_type_code
JOIN units AS u ON u.unit_id = e.unit_id
WHERE (:scope_global OR u.technical_area_id = ANY(CAST(:scope_areas AS smallint[]))
       OR u.district_id = ANY(CAST(:scope_districts AS smallint[]))
       OR u.unit_id = ANY(CAST(:scope_units AS uuid[])))
  AND (CAST(:district_id AS smallint) IS NULL OR u.district_id = CAST(:district_id AS smallint))
  AND (CAST(:unit_type_id AS smallint) IS NULL OR u.unit_type_id = CAST(:unit_type_id AS smallint))
  AND (CAST(:technical_area_id AS smallint) IS NULL
       OR u.technical_area_id = CAST(:technical_area_id AS smallint))
GROUP BY et.code, et.name, u.district_id, u.district_name
ORDER BY total_quantity DESC, et.name, u.district_name
