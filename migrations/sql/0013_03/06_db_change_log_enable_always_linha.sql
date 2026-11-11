-- Objetivo: o trigger de linha do log do banco atua mesmo com `session_replication_role = replica`.
-- Justificativa: com o padrão (ENABLE ORIGIN), um superusuário em modo `replica` desliga o
--   trigger sem DDL nenhuma; com ENABLE ALWAYS, só uma DDL explícita o desliga (013/R6.8).
-- Uso: `db_change_log`.
-- Requisitos: 013/R6.8
ALTER TABLE db_change_log ENABLE ALWAYS TRIGGER trg_db_change_log_somente_insercao;
