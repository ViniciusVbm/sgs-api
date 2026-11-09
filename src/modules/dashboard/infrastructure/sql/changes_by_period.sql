-- Objetivo: alterações de unidades, por distrito, nos últimos 7 e 30 dias.
-- Justificativa: terceira consulta da Etapa 03 da `feat/003-interface-dashboard`
--   (`alteracoes_por_periodo`), reescrita sobre a `vw_unit_history` (011/R4.4), que já junta a
--   trilha com a unidade, o tipo e o distrito. Mostra onde o cadastro está sendo mantido
--   (009/R1.4, R2.3).
--   - `count(*) FILTER (WHERE ...)` dá os dois períodos numa passada.
--   - O filtro de tipo usa uma subconsulta (`IN`), porque a view não traz o id do tipo.
-- Uso: GET /api/v1/dashboard/consultas/alteracoes-por-periodo (009/T4). A view lê a trilha por
--   `ix_audit_log_entity`.
-- Requisitos: 009/R1.4, 009/R2.3, 009/R2.5
SELECT
    district_id,
    district_name,
    count(*) FILTER (WHERE occurred_at >= now() - interval '7 days') AS last_7_days,
    count(*) AS last_30_days
FROM vw_unit_history
WHERE (:scope_global OR technical_area_id = ANY(CAST(:scope_areas AS smallint[]))
       OR district_id = ANY(CAST(:scope_districts AS smallint[]))
       OR unit_id = ANY(CAST(:scope_units AS uuid[])))
  AND (CAST(:district_id AS smallint) IS NULL OR district_id = CAST(:district_id AS smallint))
  AND (CAST(:technical_area_id AS smallint) IS NULL
       OR technical_area_id = CAST(:technical_area_id AS smallint))
  AND (CAST(:unit_type_id AS smallint) IS NULL
       OR unit_id IN (SELECT id FROM health_units
                      WHERE unit_type_id = CAST(:unit_type_id AS smallint)))
  AND occurred_at >= now() - interval '30 days'
GROUP BY district_id, district_name
ORDER BY last_30_days DESC, district_name
