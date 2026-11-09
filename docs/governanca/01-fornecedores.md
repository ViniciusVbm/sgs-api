# Cadastro e classificação de fornecedores

**Critérios de classificação:**
- **Criticidade:** Alta (parar o fornecedor para o sistema ou expõe dados), Média (degrada ou atrasa) ou Baixa.
- **Dado acessado:** nenhum, código, dado de cadastro (público) ou dado pessoal.
- **Situação:** em uso ou planejado (specs 004 e 005, não implementadas).

| # | Fornecedor / dependência | Função no sistema | Criticidade | Dado acessado | Situação | Controles existentes (evidência) |
|---|---|---|---|---|---|---|
| F01 | PostgreSQL 17 (imagem `postgres:17`, Docker Hub) | Banco de dados | Alta | Todos | Em uso | TLS `verify-full` (`docker/compose.yml`, `tests/e2e/test_tls_banco.py`); privilégio mínimo (`tests/integration/db/test_privilegios.py`) |
| F02 | Bibliotecas Python (PyPI): FastAPI, SQLAlchemy, asyncpg, Pydantic, PyJWT, cryptography, pwdlib/argon2, pyotp, limits, structlog, uvicorn, Alembic | Aplicação | Alta | Todos (em memória) | Em uso | Versões travadas no `uv.lock`; `pip-audit` e `bandit` no CI (`.github/workflows/ci.yml`); `uv sync --frozen` |
| F03 | Astral `uv` | Gerência de dependências e build | Média | Código | Em uso | Versão do `uv` fixada no `docker/Dockerfile` |
| F04 | Imagens base `python:3.13-slim-trixie`, `caddy:2`, `alpine:3.23` | Execução, proxy TLS, geração de certificados | Alta | Tráfego (Caddy) | Em uso | Tags fixadas (não por digest: ver risco R05) |
| F05 | GitHub | Repositório, PRs, CI | Média | Código (sem segredos) | Em uso | Branch protegida (ADR-0008); `secrets/` e `.env` no `.gitignore`; hook `detect-private-key` no pre-commit |
| F06 | Diretório da Secretaria (AD/OpenLDAP) | Usuários e grupos | Alta | Dado pessoal (nome, e-mail, grupos) | Planejado (004) | Ainda nenhum |
| F07 | Provedor OIDC (Keycloak ou do governo) | Login federado | Alta | Dado pessoal | Planejado (004) | Ainda nenhum; tokens próprios ES256 já isolam a sessão (ADR-0003) |
| F08 | Armazenamento S3 (AWS ou SeaweedFS) | Exportação de relatórios | Média | Dado de cadastro; trilha | Planejado (005) | Ainda nenhum (design prevê STS, SSE e URL pré-assinada) |
| F09 | Hospedagem e rede da Prefeitura | Execução em produção | Alta | Todos | A definir | Configuração recusa segredos de exemplo em prod (`src/core/config.py`, `tests/unit/core/test_config.py`) |
| F10 | Assistente de código (Claude Code) | Ferramenta de desenvolvimento | Baixa | Código | Em uso | Sem acesso a dado de produção; commits marcados com `Co-Authored-By` (registro de uso de IA) |

**Ciclo de vida (COBIT APO10, ver doc 04):** a inclusão de uma dependência nova passa por ADR (ex.: ADR-0007) e pela `steering/tech.md`. A revisão periódica é o `pip-audit` do CI e a atualização do `uv.lock` por PR. A saída de uma dependência também é registrada em ADR, como a troca do slowapi pela `limits` (emenda do ADR-0007).
