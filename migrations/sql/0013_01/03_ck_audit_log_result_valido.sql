-- Objetivo: limitar o resultado da operação aos valores do domínio.
-- Justificativa: sucesso, falha e negação explícitos, sem deduzir o sucesso da existência do
--   evento (013/R4.1). Nulo é aceito: são as linhas anteriores à 013.
-- Uso: `audit_log.result`; o mesmo conjunto de `RESULTADOS` no domínio.
-- Requisitos: 013/R4.1
ALTER TABLE audit_log ADD CONSTRAINT ck_audit_log_result_valido CHECK (
    result IS NULL OR result IN ('success', 'failure', 'denied')
);
