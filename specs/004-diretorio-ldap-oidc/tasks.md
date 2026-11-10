# 004 · Diretório LDAP e OIDC · Tarefas

- Status: Rascunho
- Depende de: 002, 003

## O que já existe no código (revisão de 09/11/2026, agente; aguarda o dono)
- T1: as colunas `users.source`, `users.external_id` e `users.synced_at`, a unicidade (`source`, `external_id`) e o CHECK `credencial_conforme_origem` já existem (migração `0002_identity`). A T1 fica com `groups`, `user_groups`, `directory_sync_runs` e a FK de `group_role_mappings.group_id` para `groups`, que a `0003_access` deixou sem FK (003, pergunta de T1).
- T5: o login local já recusa conta externa (`identity/application/login.py`), o que cobre a parte "senha local" da R4.1.
- A permissão `diretorio:sync` já está semeada para o `ADMIN_TI`.
- As bibliotecas `ldap3` e `authlib` estão em `steering/tech.md`, mas não no `pyproject.toml`: entram na T2 e na T6.
- A 003/T8 (mapeamento de grupos para papéis) só pode começar depois da T1 desta spec.

- [ ] T1. Migração com `groups`, `user_groups`, `directory_sync_runs` e colunas `source`/`external_id`
  - Requisitos: R1.5, R1.9
  - Pronto quando: `tests/integration/identity/test_directory_tables.py` passa
- [ ] T2. `DirectoryPort` e adaptador ldap3 com TLS obrigatório e busca paginada
  - Requisitos: R1.2, R1.3, R1.4, R2.2
  - Pronto quando: `tests/unit/identity/test_ldap3_adapter.py` (MOCK_SYNC) passa
- [ ] T3. Caso de uso de sincronização com upsert, desativação e rollback em falha
  - Requisitos: R1.5–R1.10
  - Pronto quando: `tests/integration/identity/test_ldap_sync.py` passa
- [ ] T4. Rotas de sincronização com trava e execuções
  - Requisitos: R1.1, R1.11
  - Pronto quando: `tests/integration/identity/test_sync_routes.py` passa
- [ ] T5. Login por bind LDAP seguido de 2FA
  - Requisitos: R2.1–R2.4, R4.1
  - Pronto quando: `tests/integration/identity/test_ldap_login.py` passa
- [ ] T6. `OidcPort` com Authlib, PKCE, state/nonce em cookie cifrado
  - Requisitos: R3.1, R3.2, R3.6
  - Pronto quando: `tests/unit/identity/test_oidc_validation.py` passa
- [ ] T7. Callback OIDC com provisionamento JIT de usuário e grupos
  - Requisitos: R3.3, R3.4, R3.5, R4.2
  - Pronto quando: `tests/integration/identity/test_oidc_callback.py` passa
- [ ] T8. Ambiente local: imagem slapd com LDIF de seed e realm Keycloak federado
  - Requisitos: R1.2
  - Pronto quando: `tests/e2e/test_login_ldap_oidc.py -m slow` passa no compose
- [ ] T9. Agendamento opcional da sincronização
  - Requisitos: R1.12
  - Pronto quando: `tests/unit/identity/test_sync_schedule.py` passa
