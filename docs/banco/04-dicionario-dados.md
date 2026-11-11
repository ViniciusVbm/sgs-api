# Dicionário de dados

Gerado do `metadata` do SQLAlchemy (`src/modules/*/infrastructure/tables.py`), que o teste `tests/integration/test_migracoes_sincronizadas.py` mantém igual às migrações (cadeia até a `0013_04`). Tipos do PostgreSQL 17.

## `districts`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | SMALLINT | não |  | PK |
| `code` | VARCHAR(20) | não |  | UNIQUE |
| `name` | VARCHAR(100) | não |  |  |
| `is_active` | BOOLEAN | não | true |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

## `technical_areas`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | SMALLINT | não |  | PK |
| `code` | VARCHAR(50) | não |  | UNIQUE |
| `name` | VARCHAR(100) | não |  |  |
| `is_active` | BOOLEAN | não | true |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

## `unit_types`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | SMALLINT | não |  | PK |
| `code` | VARCHAR(50) | não |  | UNIQUE |
| `name` | VARCHAR(100) | não |  |  |
| `technical_area_id` | SMALLINT | não |  | FK → `technical_areas.id` |
| `is_active` | BOOLEAN | não | true |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

## `equipment_types`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | SMALLINT | não |  | PK |
| `code` | VARCHAR(50) | não |  | UNIQUE |
| `name` | VARCHAR(100) | não |  |  |
| `is_active` | BOOLEAN | não | true |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

## `service_types`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | SMALLINT | não |  | PK |
| `code` | VARCHAR(50) | não |  | UNIQUE |
| `name` | VARCHAR(100) | não |  |  |
| `is_active` | BOOLEAN | não | true |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

## `health_units`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | UUID | não |  | PK |
| `district_id` | SMALLINT | não |  | FK → `districts.id` |
| `unit_type_id` | SMALLINT | não |  | FK → `unit_types.id` |
| `cnes` | VARCHAR(7) | sim |  |  |
| `name` | VARCHAR(200) | não |  |  |
| `name_normalized` | TEXT | não | gerada: `fn_normalize_name(name::text)` |  |
| `manager_name` | VARCHAR(150) | sim |  |  |
| `cep` | VARCHAR(8) | não |  |  |
| `address` | VARCHAR(200) | não |  |  |
| `neighborhood` | VARCHAR(100) | sim |  |  |
| `phone` | VARCHAR(20) | sim |  |  |
| `opening_hours` | JSONB | sim |  |  |
| `latitude` | NUMERIC(9, 6) | sim |  |  |
| `longitude` | NUMERIC(9, 6) | sim |  |  |
| `status` | VARCHAR(20) | não |  |  |
| `pending_issues` | INTEGER | não | 0 |  |
| `version` | INTEGER | não | 1 |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

- CHECK `ck_health_units_status_valido`: `status IN ('ativa', 'inativa', 'em_implantacao')`
- CHECK `ck_health_units_pending_issues_nao_negativo`: `pending_issues >= 0`
- Índice `ix_health_units_cnes` (cnes) único
- Índice `ix_health_units_district_id_name_normalized` (district_id, name_normalized) único
- Índice `ix_health_units_name_normalized_trgm` (name_normalized)

## `equipments`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | UUID | não |  | PK |
| `unit_id` | UUID | sim |  | FK → `health_units.id` (ON DELETE RESTRICT) |
| `cnes` | VARCHAR(7) | sim |  |  |
| `name` | VARCHAR(200) | não |  |  |
| `equipment_type_code` | VARCHAR(50) | não |  | FK → `equipment_types.code` (ON UPDATE CASCADE) |
| `quantity` | INTEGER | não | 1 |  |
| `status` | VARCHAR(20) | não |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

- CHECK `ck_equipments_status_valido`: `status IN ('ativo', 'inativo', 'em_manutencao')`
- CHECK `ck_equipments_quantity_positiva`: `quantity > 0`
- Índice `ix_equipments_unit_id` (unit_id)

## `services`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | UUID | não |  | PK |
| `service_type_id` | SMALLINT | não |  | FK → `service_types.id` |
| `unit_id` | UUID | sim |  | FK → `health_units.id` (ON DELETE RESTRICT) |
| `equipment_id` | UUID | sim |  | FK → `equipments.id` (ON DELETE SET NULL) |
| `name` | VARCHAR(200) | não |  |  |
| `in_cnes` | BOOLEAN | não | false |  |
| `status` | VARCHAR(20) | não |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

- CHECK `ck_services_status_valido`: `status IN ('ativo', 'inativo')`
- Índice `ix_services_equipment_id` (equipment_id)
- Índice `ix_services_unit_id` (unit_id)

## `users`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | UUID | não |  | PK |
| `username` | VARCHAR(100) | não |  | UNIQUE |
| `email` | VARCHAR(254) | sim |  | UNIQUE |
| `display_name` | VARCHAR(200) | não |  |  |
| `password_hash` | VARCHAR(255) | sim |  |  |
| `source` | VARCHAR(10) | não |  |  |
| `external_id` | VARCHAR(512) | sim |  |  |
| `is_active` | BOOLEAN | não | true |  |
| `mfa_enabled` | BOOLEAN | não | false |  |
| `mfa_secret_enc` | VARCHAR(255) | sim |  |  |
| `mfa_last_step` | BIGINT | sim |  |  |
| `mfa_challenge_jti` | UUID | sim |  |  |
| `mfa_failed_attempts` | INTEGER | não | 0 |  |
| `failed_logins` | INTEGER | não | 0 |  |
| `locked_until` | TIMESTAMP WITH TIME ZONE | sim |  |  |
| `last_login_at` | TIMESTAMP WITH TIME ZONE | sim |  |  |
| `synced_at` | TIMESTAMP WITH TIME ZONE | sim |  |  |
| `authz_version` | INTEGER | não | 0 |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

- CHECK `ck_users_username_minusculo`: `username = lower(username)`
- CHECK `ck_users_email_minusculo`: `email = lower(email)`
- CHECK `ck_users_falhas_nao_negativas`: `failed_logins >= 0`
- CHECK `ck_users_credencial_conforme_origem`: `(source = 'local' AND password_hash IS NOT NULL AND external_id IS NULL) OR (source <> 'local' AND password_hash IS NULL AND external_id IS NOT NULL)`
- CHECK `ck_users_tentativas_mfa_nao_negativas`: `mfa_failed_attempts >= 0`
- CHECK `ck_users_origem_valida`: `source IN ('local', 'ldap', 'oidc')`
- CHECK `ck_users_senha_argon2id`: `password_hash ~ '^\$argon2id\$v=19\$m=[0-9]+,t=[0-9]+,p=[0-9]+\$[A-Za-z0-9+/]+\$[A-Za-z0-9+/]+$'`
- CHECK `ck_users_mfa_com_segredo`: `NOT mfa_enabled OR mfa_secret_enc IS NOT NULL`
- UNIQUE (source, external_id)

## `sessions`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | UUID | não |  | PK |
| `user_id` | UUID | não |  | FK → `users.id` |
| `amr` | VARCHAR(20) | não |  |  |
| `ip` | VARCHAR(64) | sim |  |  |
| `user_agent` | VARCHAR(512) | sim |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `revoked_at` | TIMESTAMP WITH TIME ZONE | sim |  |  |

- Índice `ix_sessions_user_id` (user_id)

## `refresh_tokens`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | UUID | não |  | PK |
| `session_id` | UUID | não |  | FK → `sessions.id` |
| `token_hash` | CHAR(64) | não |  | UNIQUE |
| `family_id` | UUID | não |  |  |
| `expires_at` | TIMESTAMP WITH TIME ZONE | não |  |  |
| `used_at` | TIMESTAMP WITH TIME ZONE | sim |  |  |
| `revoked_at` | TIMESTAMP WITH TIME ZONE | sim |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

- CHECK `ck_refresh_tokens_token_hash_sha256`: `token_hash ~ '^[0-9a-f]{64}$'`
- Índice `ix_refresh_tokens_session_id` (session_id)

## `roles`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | UUID | não |  | PK |
| `code` | VARCHAR(50) | não |  | UNIQUE |
| `name` | VARCHAR(100) | não |  |  |
| `description` | VARCHAR(500) | não |  |  |
| `is_system` | BOOLEAN | não | false |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

## `permissions`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | UUID | não |  | PK |
| `code` | VARCHAR(100) | não |  | UNIQUE |
| `description` | VARCHAR(500) | não |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

## `role_permissions`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `role_id` | UUID | não |  | PK; FK → `roles.id` |
| `permission_id` | UUID | não |  | PK; FK → `permissions.id` |
| `max_scope` | VARCHAR(10) | não |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

- CHECK `ck_role_permissions_escopo_maximo_valido`: `max_scope IN ('global', 'area', 'distrito', 'unidade')`

## `role_assignments`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | UUID | não |  | PK |
| `user_id` | UUID | não |  | FK → `users.id` |
| `role_id` | UUID | não |  | FK → `roles.id` |
| `scope_type` | VARCHAR(10) | não |  |  |
| `scope_id` | VARCHAR(36) | sim |  |  |
| `origin` | VARCHAR(10) | não |  |  |
| `group_mapping_id` | UUID | sim |  | FK → `group_role_mappings.id` |
| `granted_by` | UUID | sim |  | FK → `users.id` |
| `valid_until` | TIMESTAMP WITH TIME ZONE | sim |  |  |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

- CHECK `ck_role_assignments_escopo_valido`: `scope_type IN ('global', 'area', 'distrito', 'unidade')`
- CHECK `ck_role_assignments_origem_conforme_mapeamento`: `(origin = 'group') = (group_mapping_id IS NOT NULL)`
- CHECK `ck_role_assignments_escopo_conforme_tipo`: `(scope_type = 'global') = (scope_id IS NULL)`
- CHECK `ck_role_assignments_origem_valida`: `origin IN ('direct', 'group')`
- Índice `ix_role_assignments_user_id` (user_id)

## `group_role_mappings`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | UUID | não |  | PK |
| `group_id` | UUID | não |  |  |
| `role_id` | UUID | não |  | FK → `roles.id` |
| `scope_type` | VARCHAR(10) | não |  |  |
| `scope_id` | VARCHAR(36) | sim |  |  |
| `created_by` | UUID | não |  | FK → `users.id` |
| `created_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |
| `updated_at` | TIMESTAMP WITH TIME ZONE | não | now() |  |

- CHECK `ck_group_role_mappings_escopo_valido`: `scope_type IN ('global', 'area', 'distrito', 'unidade')`
- CHECK `ck_group_role_mappings_escopo_conforme_tipo`: `(scope_type = 'global') = (scope_id IS NULL)`

## `audit_log`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | BIGINT | não | identity | PK |
| `occurred_at` | TIMESTAMP WITH TIME ZONE | não |  |  |
| `actor_user_id` | UUID | sim |  |  |
| `actor_roles` | JSONB | não | '[]'::jsonb |  |
| `session_id` | UUID | sim |  |  |
| `ip` | VARCHAR(64) | sim |  |  |
| `request_id` | VARCHAR(128) | sim |  |  |
| `action` | VARCHAR(100) | não |  |  |
| `entity_type` | VARCHAR(50) | sim |  |  |
| `entity_id` | VARCHAR(100) | sim |  |  |
| `changes` | JSONB | não | '[]'::jsonb |  |
| `metadata` | JSONB | não | '{}'::jsonb |  |
| `prev_hash` | CHAR(64) | não |  |  |
| `hash` | CHAR(64) | não |  |  |
| `actor_type` | VARCHAR(20) | sim |  |  |
| `origin` | VARCHAR(100) | sim |  |  |
| `user_agent` | VARCHAR(200) | sim |  |  |
| `result` | VARCHAR(10) | sim |  |  |
| `result_reason` | VARCHAR(20) | sim |  |  |

- Índice `ix_audit_log_entity` (entity_type, entity_id, audit_log.occurred_at DESC)
- CHECK `ck_audit_log_actor_type_valido`: `actor_type IS NULL OR actor_type IN ('usuario', 'anonimo', 'sistema', 'servico', 'seed', 'cli_admin')`
- CHECK `ck_audit_log_result_valido`: `result IS NULL OR result IN ('success', 'failure', 'denied')`
- CHECK `ck_audit_log_result_reason_valido`: categoria da lista fixa, obrigatória em `failure` e `denied` e proibida em `success`
- CHECK `ck_audit_log_usuario_tem_id`: `actor_type IS DISTINCT FROM 'usuario' OR actor_user_id IS NOT NULL`
- CHECK `ck_audit_log_origem_obrigatoria` (**NOT VALID**, 0013_02): `actor_type IS NOT NULL AND result IS NOT NULL` nos eventos novos; as linhas anteriores à 013 ficam fora

## `audit_chain_head`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | SMALLINT | não |  | PK |
| `last_hash` | CHAR(64) | não |  |  |

- CHECK `ck_audit_chain_head_linha_unica`: `id = 1`

## `db_change_log`

| Coluna | Tipo | Nulo | Padrão | Chave / referência |
|---|---|---|---|---|
| `id` | BIGINT | não | identity | PK |
| `occurred_at` | TIMESTAMP WITH TIME ZONE | não | clock_timestamp() | PK |
| `table_name` | TEXT | não |  |  |
| `operation` | TEXT | não |  |  |
| `row_id` | UUID | não |  |  |
| `changed_columns` | JSONB | não |  |  |
| `db_user` | TEXT | não |  |  |
| `via_api` | BOOLEAN | não |  |  |
| `txid` | BIGINT | não |  |  |

- CHECK `ck_db_change_log_operation_valido`: `operation IN ('INSERT', 'UPDATE', 'DELETE')`
- CHECK `ck_db_change_log_table_name_valido`: `table_name IN ('health_units', 'equipments', 'services')`
- Índice `ix_db_change_log_occurred_at` (db_change_log.occurred_at DESC)

