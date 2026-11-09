# Instalação, execução e testes

## Pré-requisitos
- [uv](https://docs.astral.sh/uv/). Ele instala o Python 3.13 que o projeto exige.
- GNU Make.
- Docker 26 ou mais novo, com Compose v2.

## Ambiente de desenvolvimento com Docker
```bash
uv sync --frozen
mkdir -p secrets
uv run python -m src.tools.jwt_keys    --output secrets/jwt-keys.json      # chave JWT (uma vez)
uv run python -m src.tools.crypto_keys --output secrets/crypto-keys.json   # chave de cifra (uma vez)
docker compose -f docker/compose.yml up -d --build --wait
curl -k https://localhost/health/ready
```

**O que sobe:**
- `db-certs`: gera a CA e o certificado do banco.
- `db`: PostgreSQL 17 com TLS obrigatório.
- `api`: FastAPI. Em dev, aplica as migrações na subida.
- `proxy`: Caddy, HTTPS em `https://localhost`.

O banco **não** expõe porta para o host. Para usar o `psql`:
```bash
docker compose -f docker/compose.yml exec db psql -U sgs sgs
```

**Atenção:**
- O nome do projeto compose é fixo (`sgs-api`). Rodar o `up` a partir de outra cópia do repositório **substitui** os containers que estiverem no ar e reaproveita o volume `sgs-api_db-data`.
- `down -v` apaga o banco.
- Não use `uv run alembic upgrade head` no host: o banco só aceita TLS com o nome `db`. Para rodar as migrações à mão:
  ```bash
  docker compose -f docker/compose.yml exec api alembic upgrade head
  ```

**Dados de demonstração e primeiro administrador:**
```bash
docker compose -f docker/compose.yml exec api sgs-admin seed demo
docker compose -f docker/compose.yml exec -e SGS_SENHA_INICIAL='...' api sgs-admin create-user --username admin --nome "Administrador"
```
O `seed demo` mostra uma vez a senha gerada dos 30 usuários `demo.*`; para fixá-la, use `-e SGS_SEED_SENHA=...`.

## Variáveis de ambiente
Todas estão em `.env.example`; a configuração é validada na subida (`src/core/config.py`).

| Variável | Obrigatória | Descrição |
|---|---|---|
| `APP_ENV` | sim | `dev`, `test` ou `prod`. Em prod, segredos de exemplo são recusados |
| `DATABASE_URL` | sim | Login da API (`sgs_api`, papel `sgs_app`) |
| `DATABASE_MIGRATION_URL` | em dev | Dono do banco, usado pelas migrações |
| `DATABASE_SSL_MODE`, `DATABASE_SSL_ROOT_CERT` | — | `verify-full` e a CA (o compose já configura) |
| `JWT_PRIVATE_KEYS` ou `JWT_PRIVATE_KEYS_FILE` | sim | Chaves ES256 (`src.tools.jwt_keys`) |
| `CRYPTO_KEYS` ou `CRYPTO_KEYS_FILE`, `CRYPTO_ACTIVE_KEY` | sim | Chaves AES-256-GCM do segredo TOTP (`src.tools.crypto_keys`) |
| `CORS_ORIGINS` | — | Origens do front; também valem para o anti-CSRF do refresh |
| `MFA_OBRIGATORIO` | — | `true` (padrão); `false` só em dev |
| `LOG_LEVEL`, `DEBUG` | — | Logs JSON com redação de segredos |

## Testes
```bash
make check                          # ruff, formatação, mypy, import-linter e testes rápidos
make test-all                       # inclui os slow: e2e de TLS e prova dos índices
uv run pytest tests/integration/acceptance -v   # roteiro de aceitação do MVP
```
Os testes de integração sobem um PostgreSQL 17 descartável (testcontainers), com um banco novo por teste, e não tocam no ambiente do compose. O e2e de TLS sobe o compose num projeto próprio (`sgs-api-e2e-tls`), sem o proxy, e o apaga no fim.

## SQL da disciplina
```bash
make sql-bd     # build/sql-bd.sql (estrutura + consultas) e build/sql-bd-insercao.sql (dados)
```
