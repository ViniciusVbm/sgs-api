-- Objetivo: total de alterações de unidades nos últimos 7 e 30 dias, para o resumo.
-- Justificativa: 009/R1.4, no escopo do usuário, a partir da `vw_unit_history` (011/R4.5).
-- Uso: GET /api/v1/dashboard/resumo (009/T1).
-- Requisitos: 009/R1.4, 009/R1.5, 013/R8.8
SELECT
    count(*) FILTER (WHERE occurred_at >= now() - interval '7 days') AS last_7_days,
    count(*) FILTER (WHERE occurred_at >= now() - interval '30 days') AS last_30_days
FROM vw_unit_history
-- 013/R8.8: só alterações efetivas; uma falha (`operacao.falhou`) não é alteração. Os eventos
-- anteriores à 013 têm `result` nulo e eram todos alterações.
WHERE (result IS NULL OR result = 'success')
  AND (:scope_global OR technical_area_id = ANY(CAST(:scope_areas AS smallint[]))
       OR district_id = ANY(CAST(:scope_districts AS smallint[]))
       OR unit_id = ANY(CAST(:scope_units AS uuid[])))
  AND (CAST(:district_id AS smallint) IS NULL OR district_id = CAST(:district_id AS smallint))
  AND (CAST(:technical_area_id AS smallint) IS NULL
       OR technical_area_id = CAST(:technical_area_id AS smallint))
  AND (CAST(:unit_type_id AS smallint) IS NULL
       OR unit_id IN (SELECT id FROM health_units
                      WHERE unit_type_id = CAST(:unit_type_id AS smallint)))
