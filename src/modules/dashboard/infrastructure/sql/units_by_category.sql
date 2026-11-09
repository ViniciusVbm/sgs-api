-- Objetivo: contar as unidades por status, tipo, área técnica, distrito e situação cadastral, e
--   as sem CNES, numa resposta só.
-- Justificativa: primeira consulta da Etapa 03 da `feat/003-interface-dashboard`
--   (`unidades_por_categoria`), reescrita para o esquema da 006: em vez de colunas de texto, os
--   nomes vêm das referências pela `vw_unit_inventory`. Alimenta os gráficos de distribuição do
--   dashboard (009/R1.1, R2.1).
--   - UNION ALL de agregações sobre o mesmo conjunto (`u`), já no escopo e nos filtros.
-- Uso: GET /api/v1/dashboard/consultas/unidades-por-categoria e GET /api/v1/dashboard/resumo.
-- Requisitos: 009/R1.1, 009/R1.3, 009/R2.1, 009/R2.5
WITH u AS (
    SELECT *
    FROM vw_unit_inventory
    WHERE (:scope_global OR technical_area_id = ANY(CAST(:scope_areas AS smallint[]))
       OR district_id = ANY(CAST(:scope_districts AS smallint[]))
       OR unit_id = ANY(CAST(:scope_units AS uuid[])))
      AND (CAST(:district_id AS smallint) IS NULL OR district_id = CAST(:district_id AS smallint))
  AND (CAST(:unit_type_id AS smallint) IS NULL OR unit_type_id = CAST(:unit_type_id AS smallint))
  AND (CAST(:technical_area_id AS smallint) IS NULL
       OR technical_area_id = CAST(:technical_area_id AS smallint))
)
SELECT 'status' AS categoria, status AS chave, status AS rotulo, count(*) AS quantidade
FROM u GROUP BY status
UNION ALL
SELECT 'tipo', CAST(unit_type_id AS text), unit_type_name, count(*)
FROM u GROUP BY unit_type_id, unit_type_name
UNION ALL
SELECT 'area', CAST(technical_area_id AS text), technical_area_name, count(*)
FROM u GROUP BY technical_area_id, technical_area_name
UNION ALL
SELECT 'distrito', CAST(district_id AS text), district_name, count(*)
FROM u GROUP BY district_id, district_name
UNION ALL
SELECT 'situacao_cadastral', registration_status, registration_status, count(*)
FROM u GROUP BY registration_status
UNION ALL
SELECT 'sem_cnes', 'sem_cnes', 'Sem CNES', count(*) FILTER (WHERE cnes IS NULL)
FROM u
ORDER BY categoria, rotulo
