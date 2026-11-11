-- Objetivo: um evento da trilha, com o hash e o hash anterior.
-- Justificativa: a consulta de evento individual exibe `hash` e `prev_hash` (008/R3.2), para quem
--   confere a cadeia à mão. Traz também a origem (013); IP, User-Agent e sessão só chegam a quem
--   tem `auditoria:read_acessos`: a aplicação os anula para os demais (013/R8.2).
-- Uso: GET /api/v1/auditoria/eventos/{id} (008/T3).
-- Requisitos: 008/R3.2, 013/R8.1, 013/R8.2
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
    l.hash,
    l.actor_type,
    l.origin,
    l.user_agent,
    l.result,
    l.result_reason
FROM audit_log AS l
LEFT JOIN users AS usr ON usr.id = l.actor_user_id
WHERE l.id = :id
