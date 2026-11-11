-- Objetivo: guardar na trilha o tipo de ator, a origem, o User-Agent e o resultado da operação.
-- Justificativa: eventos de sistema não tinham origem explícita e não havia campo de resultado
--   (lacunas A, C e D da spec 013). As colunas são nuláveis e sem default: as linhas antigas não
--   são reescritas e mantêm o hash, porque o conteúdo canônico só inclui esses campos quando não
--   são nulos (013, design § Emenda à spec 001). ADD COLUMN não dispara o trigger de UPDATE.
-- Uso: gravadas por `audit.registrar`; lidas pela verificação da cadeia e pelas consultas.
-- Requisitos: 013/R1.1, 013/R1.5, 013/R3.4, 013/R4.1
ALTER TABLE audit_log
    ADD COLUMN actor_type varchar(20),
    ADD COLUMN origin varchar(100),
    ADD COLUMN user_agent varchar(200),
    ADD COLUMN result varchar(10),
    ADD COLUMN result_reason varchar(20);
