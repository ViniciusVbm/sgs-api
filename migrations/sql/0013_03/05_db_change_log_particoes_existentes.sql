-- Objetivo: proteger as partições que já existem (mensais e DEFAULT) contra TRUNCATE direto e
--   deixar os triggers delas como ENABLE ALWAYS.
-- Justificativa: um TRUNCATE direto numa partição não aciona o trigger de comando da mãe
--   (013/R6.2). `ENABLE ALWAYS` faz os triggers atuarem também com
--   `session_replication_role = replica` (013/R6.8); o ALTER é feito em cada partição, além da
--   mãe, para não depender de propagação. Os nomes vêm do catálogo e entram por `format('%I')`.
-- Uso: partições de `db_change_log` existentes na data da migração; as futuras ficam com o
--   `sp_ensure_monthly_partitions` (arquivo 08).
-- Requisitos: 013/R6.2, 013/R6.8
DO $$
DECLARE
    v_particao record;
BEGIN
    FOR v_particao IN
        SELECT esquema.nspname AS esquema, filha.relname AS nome
          FROM pg_inherits herda
          JOIN pg_class filha ON filha.oid = herda.inhrelid
          JOIN pg_namespace esquema ON esquema.oid = filha.relnamespace
         WHERE herda.inhparent = 'db_change_log'::regclass
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_db_change_log_bloqueia_truncate BEFORE TRUNCATE ON %I.%I'
            ' FOR EACH STATEMENT EXECUTE FUNCTION db_change_log_somente_insercao()',
            v_particao.esquema, v_particao.nome
        );
        EXECUTE format(
            'ALTER TABLE %I.%I ENABLE ALWAYS TRIGGER trg_db_change_log_bloqueia_truncate',
            v_particao.esquema, v_particao.nome
        );
        EXECUTE format(
            'ALTER TABLE %I.%I ENABLE ALWAYS TRIGGER trg_db_change_log_somente_insercao',
            v_particao.esquema, v_particao.nome
        );
    END LOOP;
END
$$;
