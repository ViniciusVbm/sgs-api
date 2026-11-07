-- Objetivo: tirar de PUBLIC o EXECUTE que o PostgreSQL dá a todo procedimento novo.
-- Justificativa: privilégio mínimo (011/R10.1): o procedimento só é executado por quem precisa
--   dele, a aplicação (próximo arquivo). Até a 011/T3 mudar os privilégios padrão, o REVOKE
--   explícito é o que garante isso; depois dela, continua valendo (design da 011 § 0011, item 13).
-- Uso: privilégios de `sp_deactivate_unit`.
-- Requisitos: 011/R10.1
REVOKE EXECUTE ON PROCEDURE sp_deactivate_unit(IN uuid, OUT text, OUT integer) FROM PUBLIC;
