-- Objetivo: impedir evento de tipo `usuario` sem o usuário.
-- Justificativa: um evento atribuído a uma pessoa precisa dizer qual (013/R1.2); os eventos
--   automáticos usam outro tipo e não recebem usuário inventado.
-- Uso: `audit_log.actor_type` e `audit_log.actor_user_id`.
-- Requisitos: 013/R1.2
ALTER TABLE audit_log ADD CONSTRAINT ck_audit_log_usuario_tem_id CHECK (
    actor_type IS DISTINCT FROM 'usuario' OR actor_user_id IS NOT NULL
);
