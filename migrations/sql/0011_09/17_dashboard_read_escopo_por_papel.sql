-- Objetivo: limitar `dashboard:read` ao escopo de cada papel.
-- Justificativa: a matriz semeada na 0003 dava escopo máximo global a todos, e o escopo das
--   consultas nunca reduzia nada (pergunta em aberto da 011/R2.5). Pela decisão D3 (menor
--   privilégio), cada papel vê o dashboard do seu escopo: Coordenador Técnico na área, Técnico
--   Distrital no distrito e Gestor de Unidade na unidade. Gestor de Dados e Diretoria continuam
--   com a rede inteira.
-- Uso: `role_permissions` (resolução de permissões da 003).
-- Requisitos: 011/T22 (emenda de 09/11/2026); 011/R2.5
UPDATE role_permissions AS rp
SET max_scope = CASE r.code
        WHEN 'COORD_TECNICO' THEN 'area'
        WHEN 'TECNICO_DISTRITAL' THEN 'distrito'
        WHEN 'GESTOR_UNIDADE' THEN 'unidade'
    END
FROM roles AS r, permissions AS p
WHERE r.id = rp.role_id
  AND p.id = rp.permission_id
  AND p.code = 'dashboard:read'
  AND r.code IN ('COORD_TECNICO', 'TECNICO_DISTRITAL', 'GESTOR_UNIDADE');
