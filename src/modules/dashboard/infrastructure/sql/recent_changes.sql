-- Objetivo: as alterações de unidades mais recentes, com unidade, distrito, autor e ação.
-- Justificativa: quarta consulta da Etapa 03 da `feat/003-interface-dashboard`
--   (`alteracoes_recentes`), reescrita sobre a `vw_unit_history` (011/R4.4): a view já traz o
--   nome do autor (JOIN com `users`) e o distrito, sem expor dado pessoal da unidade.
-- Uso: GET /api/v1/dashboard/consultas/alteracoes-recentes e GET /api/v1/dashboard/resumo.
-- Requisitos: 009/R1.4, 009/R2.4, 009/R2.5
SELECT
    audit_id,
    occurred_at,
    action,
    unit_id,
    unit_name,
    district_name,
    actor_name
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
ORDER BY occurred_at DESC, audit_id DESC
LIMIT :limit
