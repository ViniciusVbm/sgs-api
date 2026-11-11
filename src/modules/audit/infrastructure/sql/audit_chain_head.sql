-- Objetivo: o hash que a cabeça da cadeia diz ser o do último evento.
-- Justificativa: a verificação sem período compara o hash do último evento lido com
--   `audit_chain_head.last_hash`, na mesma foto do banco (REPEATABLE READ); se alguém apagar os
--   últimos eventos, a cadeia restante continua coerente, mas o fim não bate com a cabeça
--   (013/R5.1). Só leitura, sem `FOR UPDATE`: não disputa a trava com quem grava.
-- Uso: POST /api/v1/auditoria/verificar (013/T8).
-- Requisitos: 013/R5.1, 013/R5.11
SELECT last_hash FROM audit_chain_head WHERE id = 1
