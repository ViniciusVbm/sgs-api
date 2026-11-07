# 002 · Autenticação · Design

- Status: Aprovado (Rafael, 03/10/2026)

## Rotas
| Método e rota | Acesso | Entrada | Saída | Erros | Requisitos |
|---|---|---|---|---|---|
| `POST /api/v1/auth/login` | pública, rate limit | `{username, password}` | `{mfa_required, mfa_enrollment_required, mfa_token}` | 401, 429 | R1.* |
| `POST /api/v1/auth/mfa/enroll` | `mfa_token` (finalidade `enroll`) | — | `{otpauth_uri}` | 401 | R2.1 |
| `POST /api/v1/auth/mfa/confirm` | `mfa_token` (`enroll`) | `{code}` | `{access_token, expires_in}` + cookie | 400, 401 | R2.2 |
| `POST /api/v1/auth/mfa/verify` | `mfa_token` (`verify`) | `{code}` | `{access_token, expires_in}` + cookie | 401 | R2.3–R2.6 |
| `POST /api/v1/auth/refresh` | cookie + `X-Requested-With` | — | `{access_token}` + cookie | 401, 403 | R3.4–R3.6 |
| `POST /api/v1/auth/logout` | Bearer | — | 204 | 401 | R3.7 |
| `GET /.well-known/jwks.json` | pública | — | JWKS | — | R3.2 |

## Componentes (`modules/identity`)
- `domain/users.py`: `User`, com a senha só como hash Argon2id (R1.7) e nome de usuário e e-mail em minúsculas.
- `domain/sessions.py`: `AuthSession` (o `id` é o `sid`) e `RefreshToken`, que carrega só o SHA-256 do token (R3.3).
- `domain/ports.py`: portas `UserRepository`, `SessionRepository` e `RefreshTokenRepository`; implementação com SQLAlchemy Core em `infrastructure/repository.py`, sobre a sessão de quem chama.
- `domain/passwords.py`: interface `PasswordHasher`; implementação `pwdlib` Argon2id em `infrastructure/`.
- `domain/tokens.py`: porta `TokenService` (emitir/validar JWT, emitir/validar `mfa_token` com claim `purpose`); implementação com PyJWT em `infrastructure/`.
- `domain/totp.py`: porta do verificador TOTP com registro do último passo usado (`users.mfa_last_step`) para impedir reuso; implementação com `pyotp` em `infrastructure/`.
- `core/crypto.py`: `FieldCipher` AES-256-GCM com chaves versionadas (`CRYPTO_KEYS='{"1":"base64..."}'`, `CRYPTO_ACTIVE_KEY=1`).
- `application/login.py`, `mfa.py`, `refresh.py`, `logout.py`: casos de uso.
- `api/deps.py`: `CurrentUser` (valida Bearer, carrega sessão ativa, usuário ativo).

## Chaves JWT
- Par EC P-256 em PEM via variável de ambiente ou arquivo montado (`JWT_PRIVATE_KEYS`, lista com `kid`). A chave ativa assina; todas as públicas são publicadas no JWKS, permitindo rotação sem derrubar sessões.
- `mfa_token` é um JWT curto, `aud = sgs-mfa`, com `purpose` e `jti` (para contar tentativas).

## Modelo de dados
Migração `0002_identity`: `users`, `sessions`, `refresh_tokens` (ver `docs/architecture/modelo-dados.md`), mais `users.mfa_last_step` e os contadores de falha: `failed_logins` e `locked_until` para o bloqueio (R1.4), `mfa_challenge_jti` e `mfa_failed_attempts` para a R2.6.

## Segurança
- Hash fictício para usuário inexistente (R1.3).
- Rate limit via slowapi com chave IP; bloqueio por usuário no banco (R1.4).
- Comparações de token em memória com `hmac.compare_digest`; o refresh é buscado no banco pelo hash (ver Decisões).
- Nenhum token em log; cookies com `Secure` mesmo em dev (proxy TLS local).

## Decisões
- Permissões fora do token (ADR-0003).
- TOTP obrigatório para contas locais; pode ser desligado por configuração apenas em `dev` para acelerar testes manuais.

Decididas pelo Rafael em 06/11/2026, antes da T1:
- `TokenService` e o verificador TOTP são portas (`Protocol`) em `domain/`; PyJWT e `pyotp` ficam em `infrastructure/`, porque o `domain` só importa stdlib, pydantic e `core.errors` (contrato do import-linter).
- A raiz de composição é o `src/main.py`: fábricas de repositórios e serviços ficam em `app.state`, e a camada `api` só enxerga a `application` (contrato "infrastructure só é importada pela raiz de composição").
- `src/core/ids.py` gera UUID v7 só com a biblioteca padrão, porque o Python 3.13 não tem `uuid.uuid7`.
- O comando `sgs-admin` usa `argparse`, porque o Typer não está na `steering/tech.md`.
- O 422 aparece no `contracts/openapi.yaml` como `application/problem+json`, no lugar do `HTTPValidationError` padrão da FastAPI.
- As rotas públicas ficam numa lista explícita (`/api/v1/auth/*`, `/health/*`, `/.well-known/jwks.json`), usada pelo teste de arquitetura da 003 (T5).

Decididas pelo Rafael em 06/11/2026, na revisão do PR #16 (T2):
- As tentativas da R2.6 ficam em `users`: `mfa_challenge_jti` guarda o `jti` do `mfa_token` mais recente e `mfa_failed_attempts` conta os códigos errados contra ele. Emitir um `mfa_token` troca o `jti` e zera o contador, então só o mais recente vale. No sucesso, o `jti` é limpo e o mesmo `mfa_token` não serve de novo.
- O refresh token é gerado com `secrets.token_urlsafe(32)` (43 caracteres base64url). Fora do formato hexadecimal de 64 caracteres, um token em claro nunca passa pela CHECK de SHA-256 da 0002 (`ck_refresh_tokens_token_hash_sha256`).
- O refresh é buscado pelo SHA-256 (`RefreshTokenRepository.get_by_hash`, índice único em `refresh_tokens.token_hash`), sem `hmac.compare_digest`: quem apresenta o token não escolhe o hash, então o tempo da busca não revela nada útil.

## Riscos
- Relógio do servidor fora de sincronia quebra TOTP: container usa NTP do host; janela ±1 passo.

## Estratégia de testes
- Unidade: hasher, TokenService (expiração, `aud`, `kid` desconhecido), FieldCipher (nonce único, troca de chave), TOTP (reuso).
- Integração: fluxo completo login → enroll → confirm → refresh → reuso → logout; bloqueio após 5 falhas; tempo de resposta semelhante (tolerância ampla).
- Segurança: teste que varre logs capturados procurando token/senha.
