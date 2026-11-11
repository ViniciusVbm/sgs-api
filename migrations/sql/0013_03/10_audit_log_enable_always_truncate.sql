-- Objetivo: o trigger de imutabilidade `audit_log_bloqueia_truncate` da trilha atua mesmo com
--   `session_replication_role = replica`.
-- Justificativa: criado na 0001 como ENABLE ORIGIN, o padrão; um superusuário em modo `replica`
--   o contornaria sem DDL. Com ENABLE ALWAYS, só uma DDL explícita o desliga (013/R6.8). A 0001
--   não muda; o estado do trigger é alterado aqui.
-- Uso: `audit_log`.
-- Requisitos: 013/R6.8
ALTER TABLE audit_log ENABLE ALWAYS TRIGGER audit_log_bloqueia_truncate;
