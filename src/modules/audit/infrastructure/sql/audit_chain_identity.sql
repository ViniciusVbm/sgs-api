-- Objetivo: o que identifica a cadeia e o seu tamanho, para a âncora externa.
-- Justificativa: a âncora (013/R5.4) leva o `cadeia_id` (o hash do evento de menor id, que
--   sobrevive à restauração em outro servidor e distingue bancos com o mesmo nome), o total de
--   eventos e o nome do banco, só informativo. Lida na mesma foto da verificação (013/R5.11).
-- Uso: `sgs-admin auditoria ancorar` e a verificação com âncora (013/T9).
-- Requisitos: 013/R5.3, 013/R5.4
SELECT
    (SELECT hash FROM audit_log ORDER BY id LIMIT 1) AS cadeia_id,
    (SELECT count(*) FROM audit_log) AS total,
    current_database() AS banco
