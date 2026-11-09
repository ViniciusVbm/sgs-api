-- Objetivo: tirar de PUBLIC o EXECUTE das funções de trigger criadas antes da 0011.
-- Justificativa: a 0011_03 passou a revogar EXECUTE de PUBLIC por padrão, mas as funções da 0001
--   e da 0003 nasceram antes (pergunta em aberto da 011). Só os triggers as chamam.
-- Uso: `audit_log_somente_insercao` (0001) e `trg_roles_protect_system` (0003).
-- Requisitos: 011/T21; 011/R10.1
REVOKE EXECUTE ON FUNCTION audit_log_somente_insercao(), trg_roles_protect_system() FROM PUBLIC;
