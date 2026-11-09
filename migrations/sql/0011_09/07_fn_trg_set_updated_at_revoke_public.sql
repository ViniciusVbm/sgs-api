-- Objetivo: tirar de PUBLIC o EXECUTE da função de trigger.
-- Justificativa: menor privilégio (011/R10.1); só o trigger a chama.
-- Uso: `fn_trg_set_updated_at`.
-- Requisitos: 011/T21; 011/R10.1
REVOKE EXECUTE ON FUNCTION fn_trg_set_updated_at() FROM PUBLIC;
