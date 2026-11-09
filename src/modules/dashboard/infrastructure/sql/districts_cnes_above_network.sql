-- Objetivo: listar os distritos cujo percentual de unidades sem CNES é maior que o da rede.
-- Justificativa: unidade sem CNES fica fora do cadastro federal (pilar Validar). Mostrar onde a
--   falta se concentra direciona o trabalho do Gestor de Dados (011/R2.3).
--   - Subconsulta escalar no HAVING: o percentual da "rede" é calculado uma vez sobre o mesmo
--     conjunto (`units_in_scope`) e comparado com o de cada distrito.
--   - A "rede" é o conjunto de unidades no escopo de leitura do usuário (011/R2.5): para um
--     Técnico Distrital, a rede é o próprio distrito.
--   - Unidades inativas ficam de fora: não pedem ação.
--   - Lê a `vw_unit_inventory` (011/R4.1), que já junta tipo, área e distrito.
-- Uso: GET /api/v1/dashboard/consultas/distritos-sem-cnes-acima-da-rede (011/T12).
-- Requisitos: 011/R2.3, 011/R2.5, 011/R2.7
WITH units_in_scope AS (
    SELECT unit_id, district_id, district_name, cnes
    FROM vw_unit_inventory
    WHERE (:scope_global OR technical_area_id = ANY(CAST(:scope_areas AS smallint[]))
       OR district_id = ANY(CAST(:scope_districts AS smallint[]))
       OR unit_id = ANY(CAST(:scope_units AS uuid[])))
      AND (CAST(:district_id AS smallint) IS NULL OR district_id = CAST(:district_id AS smallint))
  AND (CAST(:unit_type_id AS smallint) IS NULL OR unit_type_id = CAST(:unit_type_id AS smallint))
  AND (CAST(:technical_area_id AS smallint) IS NULL
       OR technical_area_id = CAST(:technical_area_id AS smallint))
      AND status <> 'inativa'
)
SELECT
    district_id,
    district_name,
    count(*) AS total_units,
    count(*) FILTER (WHERE cnes IS NULL) AS units_without_cnes,
    round(100.0 * count(*) FILTER (WHERE cnes IS NULL) / count(*), 2) AS percent_without_cnes,
    (SELECT round(100.0 * count(*) FILTER (WHERE cnes IS NULL) / count(*), 2)
       FROM units_in_scope) AS network_percent_without_cnes,
    count(*) OVER () AS total
FROM units_in_scope
GROUP BY district_id, district_name
HAVING 1.0 * count(*) FILTER (WHERE cnes IS NULL) / count(*) > (
    SELECT 1.0 * count(*) FILTER (WHERE cnes IS NULL) / count(*)
    FROM units_in_scope
)
ORDER BY percent_without_cnes DESC, district_name, district_id
LIMIT :limit OFFSET :offset
