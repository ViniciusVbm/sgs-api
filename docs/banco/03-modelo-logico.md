# Modelo lógico e esquema relacional

Mapeamento do conceitual para tabelas do PostgreSQL 17 (nomes no banco em inglês, convenção do projeto, `steering/structure.md`). PK sublinhada em texto como **PK**; FKs com a regra de integridade.

```
districts(id PK smallserial, code UNIQUE, name, is_active, created_at, updated_at)
technical_areas(id PK smallserial, code UNIQUE, name, is_active, created_at, updated_at)
unit_types(id PK smallserial, code UNIQUE, name, technical_area_id FK→technical_areas, is_active, …)
equipment_types(id PK smallserial, code UNIQUE, name, is_active, …)
service_types(id PK smallserial, code UNIQUE, name, is_active, …)

health_units(id PK uuid, district_id FK→districts, unit_type_id FK→unit_types, cnes UNIQUE parcial,
             name, name_normalized GERADA (fn_normalize_name) UNIQUE(district_id, name_normalized),
             manager_name, cep, address, neighborhood, phone, opening_hours jsonb, latitude, longitude,
             status CHECK(ativa|inativa|em_implantacao), pending_issues CHECK(>=0) DEFAULT 0,
             version DEFAULT 1, created_at, updated_at)
equipments(id PK uuid, unit_id FK→health_units ON DELETE RESTRICT (nulo = sem unidade),
           equipment_type_code FK→equipment_types(code) ON UPDATE CASCADE, cnes, name,
           quantity CHECK(>0) DEFAULT 1, status CHECK(ativo|inativo|em_manutencao), …)
services(id PK uuid, service_type_id FK→service_types, unit_id FK→health_units ON DELETE RESTRICT,
         equipment_id FK→equipments ON DELETE SET NULL, name, in_cnes DEFAULT false,
         status CHECK(ativo|inativo), …)

users(id PK uuid, username UNIQUE, email UNIQUE, display_name, password_hash CHECK(Argon2id PHC),
      source CHECK(local|ldap|oidc), external_id, is_active, mfa_*, failed_logins, locked_until,
      authz_version, UNIQUE(source, external_id), …)
sessions(id PK uuid, user_id FK→users, amr, ip, user_agent, revoked_at, …)
refresh_tokens(id PK uuid, session_id FK→sessions, token_hash UNIQUE CHECK(sha256), family_id,
               expires_at, used_at, revoked_at, …)
roles(id PK uuid, code UNIQUE, name, description, is_system)
permissions(id PK uuid, code UNIQUE, description)
role_permissions(PK(role_id, permission_id), role_id FK→roles, permission_id FK→permissions,
                 max_scope CHECK(global|area|distrito|unidade))
role_assignments(id PK uuid, user_id FK→users, role_id FK→roles, scope_type, scope_id,
                 origin CHECK(direct|group), group_mapping_id FK, granted_by FK→users, valid_until)
group_role_mappings(id PK uuid, group_id, role_id FK→roles, scope_type, scope_id, created_by FK)

audit_log(id PK bigint identity, occurred_at, actor_user_id, actor_roles jsonb, session_id, ip,
          request_id, action, entity_type, entity_id, changes jsonb, metadata jsonb,
          prev_hash UNIQUE, hash UNIQUE)               -- só INSERT (triggers da 0001)
audit_chain_head(id PK CHECK(id=1), last_hash)
db_change_log(PK(id, occurred_at), table_name CHECK, operation CHECK, row_id, changed_columns jsonb,
              db_user, via_api, txid) PARTITION BY RANGE(occurred_at)   -- partições mensais
```

**Normalização:** as tabelas estão na 3FN. Distrito, área e tipos são tabelas de referência em vez de texto livre, o que remove a dependência transitiva tipo → área. A exceção deliberada é `name_normalized`, uma coluna **gerada** (derivada de `name`) que existe para a unicidade e a busca, sem risco de anomalia porque o banco a mantém.

**Diferenças em relação ao modelo antigo da `feat/003-interface-dashboard`** (descartado na consolidação, doc 04 da auditoria): distrito e tipo deixam de ser texto com CHECK e viram FKs; aparecem os serviços; a auditoria passa a ser a trilha encadeada (`audit_log`) em vez da tabela `ALTERACAO`; os usuários ganham autenticação real e papéis com escopo.
