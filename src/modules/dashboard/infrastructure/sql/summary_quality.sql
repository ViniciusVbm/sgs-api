-- Objetivo: indicadores de qualidade do cadastro para o resumo do dashboard.
-- Justificativa: 009/R1.2 e R1.3 pedem o total de unidades, as com pendências de validação, o
--   total de pendências, as sem CNES e os serviços fora do CNES, no escopo do usuário (R1.5).
--   - `pending_issues` não está na view de inventário, por isso a CTE lê `health_units`.
--   - Os serviços fora do CNES vêm de uma subconsulta escalar sobre as unidades já filtradas.
-- Uso: GET /api/v1/dashboard/resumo (009/T1).
-- Requisitos: 009/R1.2, 009/R1.3, 009/R1.5, 009/R1.6
WITH u AS (
    SELECT
        hu.id AS unit_id,
        hu.district_id,
        hu.unit_type_id,
        t.technical_area_id,
        hu.cnes,
        hu.pending_issues
    FROM health_units AS hu
    JOIN unit_types AS t ON t.id = hu.unit_type_id
),
u_in_scope AS (
    SELECT *
    FROM u
    WHERE (:scope_global OR technical_area_id = ANY(CAST(:scope_areas AS smallint[]))
       OR district_id = ANY(CAST(:scope_districts AS smallint[]))
       OR unit_id = ANY(CAST(:scope_units AS uuid[])))
      AND (CAST(:district_id AS smallint) IS NULL OR district_id = CAST(:district_id AS smallint))
  AND (CAST(:unit_type_id AS smallint) IS NULL OR unit_type_id = CAST(:unit_type_id AS smallint))
  AND (CAST(:technical_area_id AS smallint) IS NULL
       OR technical_area_id = CAST(:technical_area_id AS smallint))
)
SELECT
    count(*) AS total_units,
    count(*) FILTER (WHERE pending_issues > 0) AS units_with_issues,
    coalesce(sum(pending_issues), 0) AS total_issues,
    count(*) FILTER (WHERE cnes IS NULL) AS units_without_cnes,
    (SELECT count(*)
       FROM services AS s
      WHERE NOT s.in_cnes
        AND s.unit_id IN (SELECT unit_id FROM u_in_scope)) AS services_outside_cnes
FROM u_in_scope
