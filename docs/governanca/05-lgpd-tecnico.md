# LGPD: medidas técnicas

O sistema **não trata dado de paciente**. Os dados pessoais que ele trata:

| Dado | Onde | Finalidade |
|---|---|---|
| Nome do gestor da unidade | `health_units.manager_name` | Contato institucional da unidade |
| Nome, usuário e e-mail de quem usa o sistema | `users` | Autenticação e responsabilização |
| IP e user agent | `sessions`, `audit_log` | Segurança e trilha |
| Segredo TOTP | `users.mfa_secret_enc` (cifrado) | Segundo fator |

| Princípio (art. 6º) | Medida técnica | Evidência |
|---|---|---|
| Finalidade e adequação | Cada dado tem uso declarado no modelo de dados e na spec | `docs/architecture/modelo-dados.md`; specs 002 e 006 |
| Necessidade (minimização) | A view de inventário não expõe o nome do gestor; o dashboard não mostra dado pessoal | `tests/integration/db/test_views.py`; `test_painel.py::test_inventario_pela_view_sem_dado_pessoal` |
| Segurança | Senha só em Argon2id; segredo TOTP cifrado com AES-256-GCM (chave versionada); TLS `verify-full` no banco; HTTPS no proxy; cookies `HttpOnly; Secure; SameSite=Strict` | `test_login.py`, `test_mfa.py`, `tests/e2e/test_tls_banco.py`, `test_refresh.py` |
| Prevenção | Nome do gestor mascarado (`***`) na trilha e no log do banco; logs com redação de segredos | `test_crud_unidades.py::test_trilha_mascara_o_nome_do_gestor_e_grava_o_papel`; `test_logging_redaction.py` |
| Livre acesso e transparência | `GET /api/v1/me` mostra ao usuário os papéis e permissões dele | `test_me.py` |
| Responsabilização e prestação de contas | Trilha com autor, papéis, sessão, IP, de/para; imutável e verificável | `test_audit_immutable.py`, `test_consulta_trilha.py` |
| Qualidade dos dados | Unicidade, validação de formato, consultas de qualidade | `test_crud_unidades.py`, `test_painel.py` |

**Lacunas:**
- Rotina para atender pedidos de titulares.
- Relatório de impacto (RIPD).
- Política de retenção de sessões e refresh tokens.
- Cifra em repouso do nome do gestor (hoje só mascarado nas trilhas).
- Base legal e encarregado (DPO) definidos pela Secretaria.

Essas lacunas dependem de decisões e processos fora do repositório.
