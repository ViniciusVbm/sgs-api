-- Objetivo: listar uma tabela de referência do cadastro.
-- Justificativa: preencher os formulários (006/R7.1). `{tabela}` e `{area}` são trocados na carga
--   do módulo só por nomes de uma lista fechada (`TipoDeReferencia`), nunca por valor do usuário.
-- Uso: GET /api/v1/referencias/{tipo} (006/T9).
-- Requisitos: 006/R7.1
SELECT id, code, name, is_active, {area} AS technical_area_id
FROM {tabela}
ORDER BY name, id
