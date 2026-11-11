-- Objetivo: recusar TRUNCATE do log do banco pela tabela-mãe.
-- Justificativa: trigger de TRUNCATE é de comando e não é clonado para as partições; este cobre
--   o TRUNCATE da mãe, e o arquivo seguinte põe um igual em cada partição (013/R6.2).
-- Uso: `db_change_log`.
-- Requisitos: 013/R6.2
CREATE TRIGGER trg_db_change_log_bloqueia_truncate
    BEFORE TRUNCATE ON db_change_log
    FOR EACH STATEMENT EXECUTE FUNCTION db_change_log_somente_insercao();
