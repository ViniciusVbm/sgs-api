-- Objetivo: limitar o tipo de ator aos valores do domínio.
-- Justificativa: distinguir pessoa, anônimo, sistema, serviço, seed e comando administrativo
--   sem texto livre (013/R1.1). Nulo é aceito: são as linhas anteriores à 013.
-- Uso: `audit_log.actor_type`; o mesmo conjunto de `TIPOS_DE_ATOR` no domínio.
-- Requisitos: 013/R1.1
ALTER TABLE audit_log ADD CONSTRAINT ck_audit_log_actor_type_valido CHECK (
    actor_type IS NULL
    OR actor_type IN ('usuario', 'anonimo', 'sistema', 'servico', 'seed', 'cli_admin')
);
