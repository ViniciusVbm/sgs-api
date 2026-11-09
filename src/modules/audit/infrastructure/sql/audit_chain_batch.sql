-- Objetivo: um lote da trilha em ordem de `id`, com tudo o que entra no hash.
-- Justificativa: a verificação recalcula a cadeia em lotes de 1.000 eventos, comparando cada
--   `hash` com o SHA-256 do `prev_hash` mais o conteúdo canônico, e cada `prev_hash` com o `hash`
--   do evento anterior (008/R3.1; design § Verificação da cadeia). Só leitura.
-- Uso: POST /api/v1/auditoria/verificar (008/T4).
-- Requisitos: 008/R3.1
SELECT
    id,
    occurred_at,
    action,
    actor_user_id,
    actor_roles,
    session_id,
    ip,
    request_id,
    entity_type,
    entity_id,
    changes,
    metadata,
    prev_hash,
    hash
FROM audit_log
WHERE id > :depois_de
  AND (CAST(:de AS timestamptz) IS NULL OR occurred_at >= CAST(:de AS timestamptz))
  AND (CAST(:ate AS timestamptz) IS NULL OR occurred_at < CAST(:ate AS timestamptz))
ORDER BY id
LIMIT :limit
