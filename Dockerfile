FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest \
    /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1

COPY pyproject.toml uv.lock README.md ./

COPY src ./src

# Arquivos necessários para executar as migrações
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

RUN uv sync --locked --no-dev

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "logiflow.main:app", "--host", "0.0.0.0", "--port", "8000"]