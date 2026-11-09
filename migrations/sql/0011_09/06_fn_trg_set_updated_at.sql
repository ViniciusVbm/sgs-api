-- Objetivo: função de trigger que põe a hora da transação em `updated_at` a cada UPDATE.
-- Justificativa: as escritas do cadastro são SQL escrito à mão (ADR-0009), então o `onupdate` do
--   SQLAlchemy nunca roda e `updated_at` ficaria parado na criação. A `health_units` já tem o
--   `trg_health_units_version`, que faz isso junto com a versão; esta função cobre as demais.
--   Só atualiza quando a linha muda de fato (`IS DISTINCT FROM`), para um UPDATE sem efeito não
--   parecer alteração.
-- Uso: `trg_set_updated_at` em `equipments`, `services` e nas tabelas de referência.
-- Requisitos: 011/T21 (emenda de 09/11/2026)
CREATE FUNCTION fn_trg_set_updated_at() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF to_jsonb(NEW) - 'updated_at' IS DISTINCT FROM to_jsonb(OLD) - 'updated_at' THEN
        NEW.updated_at := now();
    END IF;
    RETURN NEW;
END;
$$;
