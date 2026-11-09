-- Objetivo: aplicar os campos enviados num PATCH, só se a versão ainda for a esperada.
-- Justificativa: atualização parcial com controle de concorrência otimista (006/R3.1, R3.2). Cada
--   coluna só muda quando o seu `set_<coluna>` é verdadeiro, então o texto do SQL é fixo e
--   nenhum nome de campo vem do usuário (ADR-0009). `version` igual à esperada faz a escrita falhar
--   (nenhuma linha) se outra pessoa alterou a unidade depois da leitura: a API responde 412. A
--   versão nova vem do `trg_health_units_version` da 011 (R8); este UPDATE não a incrementa
--   (011/T17), e uma alteração feita fora da API também invalida o ETag antigo.
-- Uso: PATCH /api/v1/unidades/{id} (006/T5, 011/T17).
-- Requisitos: 006/R3.1, 006/R3.2, 011/R8.3
UPDATE health_units
SET
    name = CASE WHEN :set_name THEN :name ELSE name END,
    cnes = CASE WHEN :set_cnes THEN :cnes ELSE cnes END,
    unit_type_id = CASE WHEN :set_unit_type_id THEN :unit_type_id ELSE unit_type_id END,
    district_id = CASE WHEN :set_district_id THEN :district_id ELSE district_id END,
    cep = CASE WHEN :set_cep THEN :cep ELSE cep END,
    address = CASE WHEN :set_address THEN :address ELSE address END,
    neighborhood = CASE WHEN :set_neighborhood THEN :neighborhood ELSE neighborhood END,
    phone = CASE WHEN :set_phone THEN :phone ELSE phone END,
    manager_name = CASE WHEN :set_manager_name THEN :manager_name ELSE manager_name END,
    latitude = CASE WHEN :set_latitude THEN :latitude ELSE latitude END,
    longitude = CASE WHEN :set_longitude THEN :longitude ELSE longitude END,
    status = CASE WHEN :set_status THEN :status ELSE status END
WHERE id = :id
  AND version = :version
RETURNING
    id, name, cnes, unit_type_id, district_id, cep, address, neighborhood, phone,
    manager_name, opening_hours, latitude, longitude, status,
    pending_issues, version, created_at, updated_at
