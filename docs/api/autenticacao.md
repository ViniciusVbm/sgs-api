# Autenticação e autorização (como o front usa a API)

## Fluxo de login (spec 002)
1. `POST /api/v1/auth/login` com `{"username", "password"}`. A resposta traz `mfa_token` (vale 5 min) e uma das marcas abaixo; senha errada, usuário inexistente, bloqueado ou desativado dão o **mesmo** 401.
   - `mfa_enrollment_required: true`: o 2FA ainda não foi cadastrado.
   - `mfa_required: true`: o 2FA já existe e é preciso enviar o código.
2. Primeiro acesso:
   - `POST /api/v1/auth/mfa/enroll` com `{"mfa_token"}` devolve `otpauth_uri`, que o front mostra como QR code, uma vez.
   - `POST /api/v1/auth/mfa/confirm` com `{"mfa_token", "code"}` ativa o 2FA e entra.
3. Demais acessos: `POST /api/v1/auth/mfa/verify` com `{"mfa_token", "code"}`.
4. A resposta de confirm e verify:
   - **corpo:** `{"access_token", "token_type": "Bearer", "expires_in": 900}`. Guarde só em memória.
   - **cookie** `sgs_refresh`: `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth`, vale 8 h.
5. Chamadas: `Authorization: Bearer <access_token>`.
6. Renovação, antes de o access token vencer: `POST /api/v1/auth/refresh` com o cabeçalho `X-Requested-With: sgs` e a `Origin` do front. A `Origin` precisa estar em `CORS_ORIGINS` (anti-CSRF). O refresh é rotativo: reapresentar um já usado revoga a sessão inteira.
7. Saída: `POST /api/v1/auth/logout` com o Bearer revoga a sessão e apaga o cookie.

**Limites e bloqueios:**
- 10 tentativas de login por minuto por IP (429).
- 5 falhas seguidas bloqueiam o usuário por 15 min.
- 5 códigos TOTP errados invalidam o `mfa_token`.
- Um código TOTP não pode ser reutilizado.

**Desenvolvimento:** `MFA_OBRIGATORIO=false`, só aceito com `APP_ENV=dev`, faz o login devolver o `access_token` direto, para testes manuais.

## Autorização (spec 003)
- `GET /api/v1/me` devolve os papéis com escopo e as permissões efetivas. O front monta a tela inicial por ele.
- Toda rota de `/api/v1` exige uma permissão (`recurso:acao`) num escopo (global, área técnica, distrito ou unidade), salvo a lista pública (`/api/v1/auth/*`). O teste de arquitetura `tests/architecture/test_rotas_protegidas.py` garante isso.
- Sem permissão no escopo: 403, auditado como `acesso.negado`. Listagens e dashboard devolvem só o que está no escopo de leitura do usuário.
- A mudança de papel vale na requisição seguinte (cache de 30 s invalidado por versão).

## Primeiro administrador
```bash
SGS_SENHA_INICIAL='uma-senha-longa' docker compose -f docker/compose.yml exec \
  -e SGS_SENHA_INICIAL api sgs-admin create-user --username admin --nome "Administrador"
```
Depois, `POST /api/v1/admin/atribuicoes` (permissão `papel:assign`) atribui papéis aos demais usuários. Ninguém atribui papel a si mesmo.

## Fora desta versão
LDAP e OIDC (spec 004) e exportação para S3 (spec 005) **não estão implementados**: as specs estão em Rascunho. O modelo já reserva `users.source = ldap | oidc` e `group_role_mappings`.
