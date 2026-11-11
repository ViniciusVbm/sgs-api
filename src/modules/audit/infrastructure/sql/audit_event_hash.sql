-- Objetivo: o hash gravado de um evento, pelo id.
-- Justificativa: a âncora diz que o evento `id` tinha o hash `hash`; se o evento sumiu ou mudou,
--   a âncora não confere (013/R5.3). Lida na mesma foto da verificação.
-- Uso: verificação com âncora (013/T9).
-- Requisitos: 013/R5.3
SELECT hash FROM audit_log WHERE id = :id
