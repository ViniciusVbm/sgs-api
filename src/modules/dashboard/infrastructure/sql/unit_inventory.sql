-- Objetivo: inventário da rede, uma linha por unidade, a partir da view de inventário.
-- Justificativa: a `vw_unit_inventory` (011/R4.1) é a definição única do inventário: tipo, área,
--   distrito, status, situação cadastral (`fn_registration_status`) e as quantidades de
--   equipamentos, serviços e serviços fora do CNES. Sem dado pessoal (011/R4.2).
--   - Escopo de leitura e filtros no fragmento fixo (011/R4.3); filtro opcional por situação.
-- Uso: GET /api/v1/dashboard/inventario (011/T13).
-- Requisitos: 011/R4.1, 011/R4.2, 011/R4.3
SELECT
    unit_id,
    name,
    cnes,
    status,
    registration_status,
    unit_type_id,
    unit_type_name,
    technical_area_id,
    technical_area_name,
    district_id,
    district_name,
    equipment_count,
    service_count,
    services_outside_cnes_count,
    count(*) OVER () AS total
FROM vw_unit_inventory
WHERE (:scope_global OR technical_area_id = ANY(CAST(:scope_areas AS smallint[]))
       OR district_id = ANY(CAST(:scope_districts AS smallint[]))
       OR unit_id = ANY(CAST(:scope_units AS uuid[])))
  AND (CAST(:district_id AS smallint) IS NULL OR district_id = CAST(:district_id AS smallint))
  AND (CAST(:unit_type_id AS smallint) IS NULL OR unit_type_id = CAST(:unit_type_id AS smallint))
  AND (CAST(:technical_area_id AS smallint) IS NULL
       OR technical_area_id = CAST(:technical_area_id AS smallint))
  AND (CAST(:registration_status AS text) IS NULL
       OR registration_status = CAST(:registration_status AS text))
ORDER BY district_name, name, unit_id
LIMIT :limit OFFSET :offset
