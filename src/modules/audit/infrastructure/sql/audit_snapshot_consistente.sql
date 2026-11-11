-- Objetivo: fixar uma foto única do banco para toda a verificação da cadeia.
-- Justificativa: com escritas concorrentes, ler a cabeça e os lotes em READ COMMITTED daria um
--   falso "fim não confere" (a cabeça de um instante e os eventos de outro). Em REPEATABLE READ,
--   todas as leituras da transação veem a mesma foto; READ ONLY garante que nada é gravado nela
--   (013/R5.11). Precisa ser o primeiro comando da transação.
-- Uso: POST /api/v1/auditoria/verificar (013/T8).
-- Requisitos: 013/R5.11
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY
