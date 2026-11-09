-- Objetivo: tirar da API o DELETE das tabelas de exclusão lógica.
-- Justificativa: unidades e referências nunca são apagadas fisicamente (006/R4.2; decisão U5 da
--   011): a desativação muda `status` ou `is_active`. Os default privileges da 0001 davam DELETE
--   a `sgs_app` em toda tabela; aqui ele sai dessas, e uma falha da aplicação não consegue apagar
--   uma unidade. Equipamentos e serviços continuam com exclusão física (U5).
-- Uso: papel `sgs_app` (login `sgs_api`).
-- Requisitos: 011/T21; 006/R4.2; 011/R10.1
REVOKE DELETE ON health_units, districts, technical_areas, unit_types, equipment_types,
    service_types FROM sgs_app;
