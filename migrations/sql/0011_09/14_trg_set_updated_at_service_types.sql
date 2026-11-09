-- Objetivo: manter `service_types.updated_at` a cada alteração.
-- Justificativa: ver `06_fn_trg_set_updated_at.sql`.
-- Uso: toda escrita em `service_types`.
-- Requisitos: 011/T21 (emenda de 09/11/2026)
CREATE TRIGGER trg_set_updated_at BEFORE UPDATE ON service_types
    FOR EACH ROW EXECUTE FUNCTION fn_trg_set_updated_at();
