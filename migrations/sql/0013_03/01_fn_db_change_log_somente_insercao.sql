-- Objetivo: recusar UPDATE, DELETE e TRUNCATE no log do banco.
-- Justificativa: o `db_change_log` só pode crescer (013/R6.1, R6.2), como a trilha (`audit_log`,
--   0001). A função só levanta exceção; não é SECURITY DEFINER e não lê nada. `search_path`
--   fixo. O INSERT do `trg_registry_change_log` não passa por ela (013/R6.3).
-- Uso: triggers `trg_db_change_log_somente_insercao` (linha) e
--   `trg_db_change_log_bloqueia_truncate` (comando), na mãe e em cada partição.
-- Requisitos: 013/R6.1, 013/R6.2
CREATE FUNCTION db_change_log_somente_insercao() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    RAISE EXCEPTION 'db_change_log é somente inserção: % bloqueado', TG_OP;
END
$$;
