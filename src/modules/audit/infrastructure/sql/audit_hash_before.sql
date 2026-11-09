-- Objetivo: o hash do evento imediatamente anterior a um id.
-- Justificativa: verificando só um período, o primeiro evento dele precisa do hash do anterior
--   para conferir o `prev_hash`; sem anterior, vale o hash de gênese (64 zeros, 0001).
-- Uso: POST /api/v1/auditoria/verificar (008/T4).
-- Requisitos: 008/R3.1
SELECT hash FROM audit_log WHERE id < :id ORDER BY id DESC LIMIT 1
