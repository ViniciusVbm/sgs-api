-- Objetivo: o histórico de negócio da unidade com tipo de ator, origem e resultado, sem os
--   eventos de acesso e de auditoria.
-- Justificativa: as mesmas 14 colunas, na mesma ordem e com as mesmas junções da 0011_04 (ver o
--   cabeçalho de lá), mais `actor_type`, `origin`, `result` e `result_reason` no fim; o
--   CREATE OR REPLACE VIEW só aceita colunas novas no fim e mantém dono e privilégios (o REVOKE
--   da 0011_04/03 segue valendo). Mudanças da 013:
--   - Entram os `operacao.falhou` com a unidade na entidade, tirada do caminho da rota de forma
--     inequívoca (013/R8.7).
--   - Saem `auth.*`, `acesso.negado` e `auditoria.*`: são da trilha geral, vista só com
--     `auditoria:read` global e, os de acesso, com `read_acessos` (008/R2.2). Antes, um
--     `acesso.negado` com entidade de unidade aparecia aqui e nas contagens do dashboard.
--   - IP, User-Agent, sessão, request id e hash continuam fora (013/R8.6).
--   - Eventos anteriores à 013 saem com as quatro colunas novas nulas (013/R1.5).
-- Uso: `unit_history.sql` (GET /unidades/{id}/historico) e as consultas de alterações do
--   dashboard, que contam só resultados de sucesso (013/R8.8).
-- Requisitos: 011/R4.4, 011/R4.6, 013/R1.5, 013/R8.6, 013/R8.7
CREATE OR REPLACE VIEW vw_unit_history WITH (security_invoker = true) AS
SELECT
    l.id AS audit_id,
    l.occurred_at,
    l.action,
    l.changes,
    l.metadata,
    l.actor_user_id,
    usr.display_name AS actor_name,
    l.actor_roles,
    u.id AS unit_id,
    u.name AS unit_name,
    u.district_id,
    d.name AS district_name,
    t.name AS unit_type_name,
    t.technical_area_id,
    l.actor_type,
    l.origin,
    l.result,
    l.result_reason
FROM audit_log AS l
JOIN health_units AS u ON l.entity_type = 'unidade' AND l.entity_id = u.id::text
JOIN unit_types AS t ON t.id = u.unit_type_id
JOIN districts AS d ON d.id = u.district_id
LEFT JOIN users AS usr ON usr.id = l.actor_user_id
WHERE l.action NOT LIKE 'auth.%'
  AND l.action <> 'acesso.negado'
  AND l.action NOT LIKE 'auditoria.%';
