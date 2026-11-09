-- Objetivo: um evento da trilha, com o hash e o hash anterior.
-- Justificativa: a consulta de evento individual exibe `hash` e `prev_hash` (008/R3.2), para quem
--   confere a cadeia à mão.
-- Uso: GET /api/v1/auditoria/eventos/{id} (008/T3).
-- Requisitos: 008/R3.2
SELECT
    l.id,
    l.occurred_at,
    l.action,
    l.actor_user_id,
    usr.display_name AS actor_name,
    l.actor_roles,
    l.session_id,
    l.ip,
    l.request_id,
    l.entity_type,
    l.entity_id,
    l.changes,
    l.metadata,
    l.prev_hash,
    l.hash
FROM audit_log AS l
LEFT JOIN users AS usr ON usr.id = l.actor_user_id
WHERE l.id = :id
