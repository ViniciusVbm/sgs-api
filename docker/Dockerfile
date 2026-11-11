# Imagem da API (spec 001, R1.1): dependências travadas pelo uv.lock e usuário sem privilégios.
# Contexto de build: a raiz do repositório (ver docker/compose.yml).

FROM python:3.13-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependências primeiro, numa camada própria: só mudam quando o uv.lock muda.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Código. O projeto fica instalado em modo editável apontando para /app: é daqui que a API lê
# alembic.ini e migrations/ para aplicar as migrações na subida em dev.
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
# Massa de demonstração do `sgs-admin seed demo` (spec 010); só dados fictícios.
COPY seeds ./seeds
RUN uv sync --frozen --no-dev


FROM python:3.13-slim-trixie AS runtime
RUN groupadd --system sgs && useradd --system --gid sgs --home-dir /app --no-create-home sgs
WORKDIR /app
COPY --from=build --chown=sgs:sgs /app /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
USER sgs
EXPOSE 8000

# X-Forwarded-* só valem vindos dos endereços de FORWARDED_ALLOW_IPS, que o uvicorn lê do
# ambiente: no compose, o IP fixo do proxy (/32; spec 013, T4). Sem a variável, o uvicorn confia
# só em 127.0.0.1. Nunca use "*": qualquer contêiner da rede escolheria o IP da auditoria.
CMD ["uvicorn", "--factory", "src.main:create_app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", \
     "--no-access-log", "--no-server-header"]
