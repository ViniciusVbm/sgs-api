-- Objetivo: trilha geral de auditoria, paginada, com filtros.
-- Justificativa: o Auditor consulta todos os eventos (008/R2.1). Os eventos de acesso (`auth.*`,
--   `acesso.negado`) só aparecem para quem tem `auditoria:read_acessos` (R2.2): o parâmetro
--   `incluir_acessos` vem da permissão, nunca do cliente.
--   - Filtros: período, ação (prefixo, como `unidade.`), tipo e id da entidade, autor.
--   - LEFT JOIN com `users` para o nome do autor; eventos do sistema não têm autor.
--   - 013: tipo de ator, origem e resultado entram; IP, User-Agent, sessão e request id não
--     (R8.6). `auditoria.evento_consultado` é evento de acesso, como `auth.*` (R7.4).
-- Uso: GET /api/v1/auditoria/eventos (008/T1, T3).
-- Requisitos: 008/R2.1, 008/R2.2, 008/R2.3, 013/R7.4, 013/R8.4, 013/R8.6
SELECT
    l.id,
    l.occurred_at,
    l.action,
    l.actor_user_id,
    usr.display_name AS actor_name,
    l.actor_roles,
    l.entity_type,
    l.entity_id,
    l.changes,
    l.metadata,
    l.actor_type,
    l.origin,
    l.result,
    l.result_reason,
    count(*) OVER () AS total
FROM audit_log AS l
LEFT JOIN users AS usr ON usr.id = l.actor_user_id
WHERE (CAST(:de AS timestamptz) IS NULL OR l.occurred_at >= CAST(:de AS timestamptz))
  AND (CAST(:ate AS timestamptz) IS NULL OR l.occurred_at < CAST(:ate AS timestamptz))
  AND (CAST(:acao AS text) IS NULL OR l.action LIKE CAST(:acao AS text) || '%')
  AND (CAST(:entidade_tipo AS text) IS NULL OR l.entity_type = CAST(:entidade_tipo AS text))
  AND (CAST(:entidade_id AS text) IS NULL OR l.entity_id = CAST(:entidade_id AS text))
  AND (CAST(:autor AS uuid) IS NULL OR l.actor_user_id = CAST(:autor AS uuid))
  AND (CAST(:incluir_acessos AS boolean)
       OR NOT (l.action LIKE 'auth.%' OR l.action IN ('acesso.negado', 'auditoria.evento_consultado')))
ORDER BY l.id DESC
LIMIT :limit OFFSET :offset
