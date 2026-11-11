-- Objetivo: o trigger de TRUNCATE da mãe do log do banco atua mesmo em modo `replica`.
-- Justificativa: a mesma do arquivo anterior (013/R6.8).
-- Uso: `db_change_log`.
-- Requisitos: 013/R6.8
ALTER TABLE db_change_log ENABLE ALWAYS TRIGGER trg_db_change_log_bloqueia_truncate;
