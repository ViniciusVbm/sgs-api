-- Objetivo: tirar de PUBLIC o EXECUTE da função de imutabilidade do log do banco.
-- Justificativa: só os triggers a chamam, como as demais funções de trigger (011/R10.1).
-- Uso: `db_change_log_somente_insercao()`.
-- Requisitos: 013/R6.1, 011/R10.1
REVOKE EXECUTE ON FUNCTION db_change_log_somente_insercao() FROM PUBLIC;
