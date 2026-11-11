-- Objetivo: exigir a categoria em falha e negação e recusá-la em sucesso.
-- Justificativa: diferenciar autenticação, autorização, validação, conflito, precondição e erro
--   interno (013/R4.1). Sucesso e linhas antigas não têm categoria.
-- Uso: `audit_log.result_reason`; o mesmo conjunto de `CATEGORIAS` no domínio.
-- Requisitos: 013/R4.1
ALTER TABLE audit_log ADD CONSTRAINT ck_audit_log_result_reason_valido CHECK (
    (
        result_reason IS NULL
        OR result_reason IN (
            'autenticacao', 'autorizacao', 'validacao', 'conflito', 'precondicao', 'erro_interno'
        )
    )
    AND (result IS DISTINCT FROM 'failure' OR result_reason IS NOT NULL)
    AND (result IS DISTINCT FROM 'denied' OR result_reason IS NOT NULL)
    AND (result_reason IS NULL OR result IN ('failure', 'denied'))
);
