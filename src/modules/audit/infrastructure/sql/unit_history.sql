-- Objetivo: histórico de uma unidade, do mais recente ao mais antigo, paginado e filtrado.
-- Justificativa: a `vw_unit_history` (011/R4.4) é a definição única do histórico: junta a trilha
--   com a unidade, o tipo, o distrito e o autor (4 JOINs), e já inclui os eventos de equipamentos
--   e serviços da unidade, que são gravados com `entity_type = 'unidade'` (006/R5.3). A 008/R1
--   é servida por ela (011/R4.5).
--   - Filtros (008/R1.3): período, autor e campo alterado (`changes @> ...`, jsonb).
--   - O escopo já foi conferido pela rota (`auditoria:read` no escopo da unidade).
--   - 013: tipo de ator, origem e resultado, sem IP, User-Agent, sessão nem request id.
-- Uso: GET /api/v1/unidades/{id}/historico (011/T14, 008/T2). Lê a trilha por
--   `ix_audit_log_entity` (011/R1.1).
-- Requisitos: 008/R1.1, 008/R1.2, 008/R1.3, 011/R4.5, 013/R8.4, 013/R8.7
SELECT
    audit_id,
    occurred_at,
    action,
    changes,
    metadata,
    actor_user_id,
    actor_name,
    actor_roles,
    actor_type,
    origin,
    result,
    result_reason,
    count(*) OVER () AS total
FROM vw_unit_history
WHERE unit_id = :unit_id
  AND (CAST(:de AS timestamptz) IS NULL OR occurred_at >= CAST(:de AS timestamptz))
  AND (CAST(:ate AS timestamptz) IS NULL OR occurred_at < CAST(:ate AS timestamptz))
  AND (CAST(:autor AS uuid) IS NULL OR actor_user_id = CAST(:autor AS uuid))
  AND (CAST(:campo AS text) IS NULL
       OR changes @> jsonb_build_array(jsonb_build_object('campo', CAST(:campo AS text))))
ORDER BY occurred_at DESC, audit_id DESC
LIMIT :limit OFFSET :offset
