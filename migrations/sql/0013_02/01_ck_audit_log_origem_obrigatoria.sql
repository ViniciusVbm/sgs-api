-- Objetivo: exigir tipo de ator e resultado em todo evento novo da trilha.
-- Justificativa: depois da 013 (T2, T5, T6), todo caminho de gravação preenche os dois campos
--   (013/R1.6). `NOT VALID` faz o PostgreSQL conferir só as linhas inseridas daqui em diante: os
--   eventos anteriores à 013, com os campos nulos, continuam válidos e com o mesmo hash, sem
--   reescrita. NUNCA rodar `VALIDATE CONSTRAINT`: falharia nas linhas antigas e a correção
--   exigiria reescrever o histórico. O `pg_dump` mantém a constraint como `NOT VALID`.
-- Uso: `audit_log.actor_type` e `audit_log.result`, gravados por `audit.registrar`.
-- Requisitos: 013/R1.6
ALTER TABLE audit_log ADD CONSTRAINT ck_audit_log_origem_obrigatoria CHECK (
    actor_type IS NOT NULL AND result IS NOT NULL
) NOT VALID;
