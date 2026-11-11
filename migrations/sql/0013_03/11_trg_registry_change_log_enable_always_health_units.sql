-- Objetivo: o trigger de log do cadastro em `health_units` grava mesmo com
--   `session_replication_role = replica`.
-- Justificativa: em modo `replica`, um trigger ENABLE ORIGIN não dispara, e a alteração feita
--   assim não entraria no log do banco. Com ENABLE ALWAYS, ela entra (013/R6.8).
-- Uso: `health_units`.
-- Requisitos: 013/R6.8, 011/R7.1
ALTER TABLE health_units ENABLE ALWAYS TRIGGER trg_registry_change_log;
