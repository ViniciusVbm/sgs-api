-- Objetivo: incluir um item de referência.
-- Justificativa: só o Gestor de Dados mantém as referências (006/R7.2). `ON CONFLICT DO NOTHING`
--   devolve nenhuma linha quando o código repete outro (409). Ver `reference_list.sql`.
-- Uso: POST /api/v1/referencias/{tipo} (006/T9), exceto tipos de unidade.
-- Requisitos: 006/R7.2
INSERT INTO {tabela} (code, name)
VALUES (:code, :name)
ON CONFLICT DO NOTHING
RETURNING id, code, name, is_active, {area} AS technical_area_id
