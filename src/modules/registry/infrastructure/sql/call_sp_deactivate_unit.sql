-- Objetivo: desativar a unidade pelo procedimento da 011.
-- Justificativa: a regra de desativação (trava, inexistente com SQLSTATE SGS01, já inativa sem
--   alteração) fica num lugar só, o `sp_deactivate_unit` (011/R6); a API só o chama e traduz o
--   resultado. Os parâmetros OUT voltam como colunas da linha do CALL.
-- Uso: POST /api/v1/unidades/{id}/desativar (006/T6, 011/T16).
-- Requisitos: 006/R4.1, 011/R6.2, 011/R6.3, 011/R6.4
CALL sp_deactivate_unit(:id, NULL, NULL)
