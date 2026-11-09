-- Objetivo: listar as unidades que ofertam ao menos um serviço que não consta no CNES.
-- Justificativa: serviço fora do CNES não entra no faturamento nem nos indicadores federais; o
--   Gestor de Dados precisa saber onde regularizar (011/R2.4).
--   - Subconsulta correlacionada com EXISTS: para cada unidade, basta achar um serviço com
--     `in_cnes` falso; o PostgreSQL para na primeira linha (semi join).
--   - Escopo de leitura e filtros no fragmento fixo (011/R2.5, R2.7).
--   - Lê a `vw_unit_inventory`, que traz a contagem `services_outside_cnes_count`.
-- Uso: GET /api/v1/dashboard/consultas/unidades-com-servico-fora-do-cnes (011/T12). A
--   subconsulta procura os serviços da unidade por `ix_services_unit_id`.
-- Requisitos: 011/R2.4, 011/R2.5, 011/R2.7
SELECT
    i.unit_id,
    i.name,
    i.cnes,
    i.unit_type_name,
    i.district_name,
    i.services_outside_cnes_count,
    count(*) OVER () AS total
FROM vw_unit_inventory AS i
WHERE (:scope_global OR technical_area_id = ANY(CAST(:scope_areas AS smallint[]))
       OR district_id = ANY(CAST(:scope_districts AS smallint[]))
       OR unit_id = ANY(CAST(:scope_units AS uuid[])))
  AND (CAST(:district_id AS smallint) IS NULL OR district_id = CAST(:district_id AS smallint))
  AND (CAST(:unit_type_id AS smallint) IS NULL OR unit_type_id = CAST(:unit_type_id AS smallint))
  AND (CAST(:technical_area_id AS smallint) IS NULL
       OR technical_area_id = CAST(:technical_area_id AS smallint))
  AND EXISTS (
      SELECT 1
      FROM services AS s
      WHERE s.unit_id = i.unit_id
        AND NOT s.in_cnes
  )
ORDER BY i.district_name, i.name, i.unit_id
LIMIT :limit OFFSET :offset
