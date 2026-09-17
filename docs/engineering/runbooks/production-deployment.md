# Operational Runbook: Production Container Deployment

**Runbook ID**: `RB-OPS-002`  
**Classification**: Deployment Procedure  
**Target Services**: Docker Compose Production Stack (`infra/docker/docker-compose.prod.yml`)

---

## 1. Pre-Deployment Health & Safety Gates

Prior to initiating any production deployment, execute the following non-negotiable gates:
1. **Repository Cleanliness**: Git tree must be clean with all commits tagged.
2. **Acceptance Suite Verification**:
   ```powershell
   .\.venv\Scripts\python.exe scripts/run_acceptance_suite.py
   ```
3. **Benchmark Regression Gate**:
   ```powershell
   .\.venv\Scripts\python.exe benchmark.py regression --baseline benchmark_report.json --concurrency 4
   ```
4. **Secrets Check**: Verify that production environment variables are injected via a secret manager (AWS Secrets Manager, GCP Secret Manager, or Vault). Never pass unencrypted secrets in source files or CLI arguments.

---

## 2. Deployment Sequence

### Step 1: Pull Production Images & Verify Hashes
```bash
docker compose -f infra/docker/docker-compose.prod.yml pull
```

### Step 2: Apply Database Migrations (Zero Downtime)
Execute migration runner container against production PostgreSQL database:
```bash
docker compose -f infra/docker/docker-compose.prod.yml run --rm api alembic upgrade head
```

### Step 3: Rolling Restart of Backend Services
```bash
# 1. Update backend core containers
docker compose -f infra/docker/docker-compose.prod.yml up -d --no-deps api

# 2. Wait for liveness and readiness probes
curl --fail --retry 10 --retry-delay 3 http://localhost:8000/api/v1/health

# 3. Update background workers
docker compose -f infra/docker/docker-compose.prod.yml up -d --no-deps worker

# 4. Update MCP server
docker compose -f infra/docker/docker-compose.prod.yml up -d --no-deps mcp-server

# 5. Update web frontend
docker compose -f infra/docker/docker-compose.prod.yml up -d --no-deps web
```

---

## 3. Post-Deployment Smoke Test & Monitoring

1. Inspect container health:
   ```bash
   docker compose -f infra/docker/docker-compose.prod.yml ps
   ```
2. Check error logs:
   ```bash
   docker compose -f infra/docker/docker-compose.prod.yml logs -f --tail=50 api | grep -i error
   ```
3. Verify Prometheus metrics endpoint:
   ```bash
   curl http://localhost:8000/metrics
   ```
