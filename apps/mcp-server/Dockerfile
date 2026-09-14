FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Security: Create non-root system user and group
RUN groupadd -g 1001 mcpuser && \
    useradd -u 1001 -g mcpuser -m -s /bin/bash mcpuser

COPY pyproject.toml README.md* ./
RUN pip install --no-cache-dir .

COPY app/ ./app/

RUN chown -R mcpuser:mcpuser /app

USER mcpuser

EXPOSE 8001

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.server.main:app", "--host", "0.0.0.0", "--port", "8001"]
