# Multi-stage production Dockerfile for CodeGuard AI API and Worker with Phase 2 Code Intelligence
FROM python:3.12-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpq5 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy packages and API definition
COPY packages/code-intelligence ./packages/code-intelligence
COPY apps/api/pyproject.toml apps/api/README.md ./apps/api/

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ./packages/code-intelligence && \
    pip install --no-cache-dir -e ./apps/api

WORKDIR /app/apps/api
COPY apps/api/app/ ./app/
COPY apps/api/alembic/ ./alembic/
COPY apps/api/alembic.ini ./

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
