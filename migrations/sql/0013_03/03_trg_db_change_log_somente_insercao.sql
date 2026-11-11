-- Objetivo: recusar UPDATE e DELETE de linha no log do banco, pela mãe e direto nas partições.
-- Justificativa: trigger de linha numa tabela particionada é clonado pelo PostgreSQL 17 para as
--   partições que existem e para as que forem criadas, inclusive a DEFAULT; vale para quem
--   escreve pela mãe e para quem escreve direto numa partição, inclusive o dono e o
--   superusuário, enquanto o trigger estiver habilitado (013/R6.1, R6.4).
-- Uso: `db_change_log` e todas as suas partições.
-- Requisitos: 013/R6.1, 013/R6.4
CREATE TRIGGER trg_db_change_log_somente_insercao
    BEFORE UPDATE OR DELETE ON db_change_log
    FOR EACH ROW EXECUTE FUNCTION db_change_log_somente_insercao();
