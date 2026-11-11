-- Objetivo: a mesma do `sp_ensure_monthly_partitions` da 0011_08 (partições mensais do log do
--   banco, do mês atual até N meses à frente, sem apagar nenhuma), com a partição nova já
--   protegida.
-- Justificativa: o corpo é o da 0011_08 (ver o cabeçalho de lá), mais três comandos depois de
--   cada CREATE TABLE: o trigger de TRUNCATE na partição (trigger de comando não é clonado da
--   mãe) e ENABLE ALWAYS nele e no trigger de linha clonado (013/R6.4, R6.8). Continua SECURITY
--   DEFINER com o `sgs_owner` como dono (CREATE OR REPLACE com `SET LOCAL ROLE`), que é o dono
--   das partições e da função de imutabilidade. Nunca faz DROP nem DETACH.
-- Uso: `sgs-admin banco particoes [--meses N]` e qualquer CALL futura.
-- Requisitos: 011/R6.5, 011/R6.6, 013/R6.4, 013/R6.8
CREATE OR REPLACE PROCEDURE sp_ensure_monthly_partitions(p_table regclass, p_months_ahead integer)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_schema name;
    v_tabela name;
    v_chave name;
    v_default name;
    v_mes record;
    v_de text;
    v_ate text;
    v_ocupado boolean;
    c_meses CURSOR FOR
        SELECT meses.inicio,
               meses.inicio + interval '1 month' AS fim,
               v_tabela || to_char(meses.inicio, '"_y"YYYY"m"MM') AS particao
          FROM generate_series(
                   date_trunc('month', now() AT TIME ZONE 'UTC'),
                   date_trunc('month', now() AT TIME ZONE 'UTC')
                       + make_interval(months => p_months_ahead),
                   interval '1 month'
               ) AS meses (inicio)
          LEFT JOIN (pg_inherits herda JOIN pg_class existente ON existente.oid = herda.inhrelid)
                 ON herda.inhparent = p_table
                AND existente.relname = v_tabela || to_char(meses.inicio, '"_y"YYYY"m"MM')
         WHERE existente.oid IS NULL
         ORDER BY meses.inicio;
BEGIN
    IF p_months_ahead IS NULL OR p_months_ahead < 0 THEN
        RAISE EXCEPTION 'sp_ensure_monthly_partitions: informe 0 ou mais meses à frente'
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    SELECT esquema.nspname, mae.relname, chave.attname, padrao.relname
      INTO v_schema, v_tabela, v_chave, v_default
      FROM pg_partitioned_table particionada
      JOIN pg_class mae ON mae.oid = particionada.partrelid
      JOIN pg_namespace esquema ON esquema.oid = mae.relnamespace
      JOIN pg_attribute chave
        ON chave.attrelid = particionada.partrelid
       AND chave.attnum = particionada.partattrs[0]
      LEFT JOIN pg_class padrao ON padrao.oid = particionada.partdefid
     WHERE particionada.partrelid = p_table
       AND particionada.partstrat = 'r'
       AND particionada.partnatts = 1;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'sp_ensure_monthly_partitions: % não é particionada por intervalo de uma coluna', p_table
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    OPEN c_meses;
    LOOP
        FETCH c_meses INTO v_mes;
        EXIT WHEN NOT FOUND;

        IF v_default IS NOT NULL THEN
            EXECUTE format('LOCK TABLE %I.%I IN SHARE ROW EXCLUSIVE MODE', v_schema, v_default);
            EXECUTE format(
                'SELECT EXISTS (SELECT 1 FROM ONLY %I.%I WHERE %I >= $1 AND %I < $2)',
                v_schema, v_default, v_chave, v_chave
            )
               INTO v_ocupado
              USING v_mes.inicio AT TIME ZONE 'UTC', v_mes.fim AT TIME ZONE 'UTC';
            IF v_ocupado THEN
                RAISE WARNING '%: o mês % já tem registros na partição %; a partição % não foi criada e os registros ficam onde estão',
                    v_tabela, to_char(v_mes.inicio, 'YYYY-MM'), v_default, v_mes.particao;
                CONTINUE;
            END IF;
        END IF;

        v_de := to_char(v_mes.inicio, 'YYYY-MM-DD HH24:MI:SS') || '+00';
        v_ate := to_char(v_mes.fim, 'YYYY-MM-DD HH24:MI:SS') || '+00';
        EXECUTE format(
            'CREATE TABLE %I.%I PARTITION OF %I.%I FOR VALUES FROM (%L) TO (%L)',
            v_schema, v_mes.particao, v_schema, v_tabela, v_de, v_ate
        );
        -- 013/R6.4, R6.8: a partição nova nasce protegida contra TRUNCATE direto e com os
        -- triggers ENABLE ALWAYS (o de linha vem clonado da mãe).
        EXECUTE format(
            'CREATE TRIGGER trg_db_change_log_bloqueia_truncate BEFORE TRUNCATE ON %I.%I'
            ' FOR EACH STATEMENT EXECUTE FUNCTION db_change_log_somente_insercao()',
            v_schema, v_mes.particao
        );
        EXECUTE format(
            'ALTER TABLE %I.%I ENABLE ALWAYS TRIGGER trg_db_change_log_bloqueia_truncate',
            v_schema, v_mes.particao
        );
        EXECUTE format(
            'ALTER TABLE %I.%I ENABLE ALWAYS TRIGGER trg_db_change_log_somente_insercao',
            v_schema, v_mes.particao
        );
        RAISE NOTICE 'partição % criada (% a %)', v_mes.particao, v_de, v_ate;
    END LOOP;
    CLOSE c_meses;
END
$$;
