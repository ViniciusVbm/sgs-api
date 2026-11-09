-- Objetivo: listar as unidades no escopo de leitura do usuário, com busca, filtros, ordenação e
--   paginação.
-- Justificativa: a listagem é a porta de entrada do cadastro (006/R2). A busca `q` compara o
--   nome normalizado (sem acento, caixa e espaços extras) pela mesma `fn_normalize_name` que gera
--   a coluna, e o começo do CNES; com `q`, as mais parecidas vêm primeiro (`similarity`, do
--   `pg_trgm`). Os caracteres curinga do LIKE vindos do usuário são escapados.
--   - Escopo (spec 003): fragmento fixo com os parâmetros de escopo; a área técnica vem do tipo.
--   - Filtros combináveis: tipo, área técnica, distrito, status e com pendências (R2.3).
--   - Ordem (R2.4): nome (padrão), distrito ou data de atualização (mais recente primeiro).
--   - `count(*) OVER ()` dá o total na mesma passada.
-- Uso: GET /api/v1/unidades (006/T4). A busca usa `ix_health_units_name_normalized_trgm`.
-- Requisitos: 006/R2.1, 006/R2.2, 006/R2.3, 006/R2.4, 006/R2.6
WITH units AS (
    SELECT
        hu.id AS unit_id,
        t.technical_area_id,
        hu.*
    FROM health_units AS hu
    JOIN unit_types AS t ON t.id = hu.unit_type_id
),
termo AS (
    SELECT
        CAST(:q AS text) AS q,
        replace(replace(replace(fn_normalize_name(CAST(:q AS text)), '\', '\\'), '%', '\%'),
                '_', '\_') AS termo_nome,
        replace(replace(replace(CAST(:q AS text), '\', '\\'), '%', '\%'), '_', '\_') AS termo_cnes
)
SELECT
    id, name, cnes, unit_type_id, district_id, cep, address, neighborhood, phone,
    manager_name, opening_hours, latitude, longitude, status,
    pending_issues, version, created_at, updated_at,
    count(*) OVER () AS total
FROM units, termo
WHERE (:scope_global OR technical_area_id = ANY(CAST(:scope_areas AS smallint[]))
       OR district_id = ANY(CAST(:scope_districts AS smallint[]))
       OR unit_id = ANY(CAST(:scope_units AS uuid[])))
  AND (termo.q IS NULL
       OR name_normalized LIKE '%' || termo.termo_nome || '%'
       OR cnes LIKE termo.termo_cnes || '%')
  AND (CAST(:unit_type_id AS smallint) IS NULL OR unit_type_id = CAST(:unit_type_id AS smallint))
  AND (CAST(:technical_area_id AS smallint) IS NULL
       OR technical_area_id = CAST(:technical_area_id AS smallint))
  AND (CAST(:district_id AS smallint) IS NULL OR district_id = CAST(:district_id AS smallint))
  AND (CAST(:status AS text) IS NULL OR status = CAST(:status AS text))
  AND (CAST(:com_pendencias AS boolean) IS NULL
       OR (pending_issues > 0) = CAST(:com_pendencias AS boolean))
ORDER BY
    CASE WHEN termo.q IS NOT NULL THEN similarity(name_normalized, fn_normalize_name(termo.q)) END
        DESC NULLS LAST,
    CASE WHEN CAST(:ordem AS text) = 'distrito' THEN district_id END,
    CASE WHEN CAST(:ordem AS text) = 'atualizacao' THEN updated_at END DESC,
    name_normalized,
    id
LIMIT :limit OFFSET :offset
