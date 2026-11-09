-- Objetivo: listar as partições do log do banco, com o intervalo e a quantidade de linhas.
-- Justificativa: mostra o efeito do procedimento com cursor `sp_ensure_monthly_partitions`
--   (011/R6.5 a R6.7): quais meses já têm partição e quanto cada uma guarda (011/R6.9).
--   - Catálogo do PostgreSQL: `pg_inherits` liga a mãe às filhas; o limite vem de
--     `pg_get_expr(relpartbound)`. A contagem usa uma subconsulta por partição, sobre a tabela-mãe
--     com o próprio intervalo, para não montar SQL dinâmico.
-- Uso: GET /api/v1/auditoria/banco/particoes (011/T15).
-- Requisitos: 011/R6.9
SELECT
    filha.relname AS name,
    pg_get_expr(filha.relpartbound, filha.oid) AS bound,
    (SELECT count(*) FROM db_change_log AS l WHERE l.tableoid = filha.oid) AS row_count
FROM pg_inherits AS herda
JOIN pg_class AS mae ON mae.oid = herda.inhparent
JOIN pg_class AS filha ON filha.oid = herda.inhrelid
WHERE mae.relname = 'db_change_log'
ORDER BY filha.relname
