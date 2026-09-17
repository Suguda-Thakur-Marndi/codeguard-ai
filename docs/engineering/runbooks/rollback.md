# Operational Runbook: Production Rollback & Downgrade Procedure

**Runbook ID**: `RB-OPS-011`  
**Classification**: Rollback Standard Operating Procedure  
**Target Services**: Docker Container Fleet, Database Schema

---

## 1. Rollback Decision Triggers

Initiate immediate rollback if any of the following occur post-deployment:
- API 5xx error rate exceeds 1% over 5 minutes.
- Celery queue latency exceeds 120 seconds.
- Liveness/readiness probes fail repeatedly.
- Corrupted review comments published to customer repositories.

---

## 2. Container Fleet Rollback

Re-deploy the previous certified image tags:
```bash
# 1. Update image tags to previous stable version (e.g., v0.1.0-prev)
export CODEGUARD_IMAGE_TAG="v0.1.0-certified"

# 2. Rolling restart back to stable release
docker compose -f infra/docker/docker-compose.prod.yml up -d --no-deps api worker mcp-server web
```

---

## 3. Database Schema Rollback (If Required)

If the failed release introduced an incompatible Alembic revision:
1. Identify the target rollback revision ID:
   ```bash
   docker compose -f infra/docker/docker-compose.prod.yml run --rm api alembic history --verbose
   ```
2. Execute downgrade to the previous stable revision:
   ```bash
   docker compose -f infra/docker/docker-compose.prod.yml run --rm api alembic downgrade <target_revision_id>
   ```
3. Verify table schema status:
   ```bash
   docker compose -f infra/docker/docker-compose.prod.yml run --rm api alembic current
   ```

---

## 4. Post-Rollback Smoke Test

Confirm operational health across all services:
```powershell
curl http://localhost:8000/api/v1/health
curl http://localhost:8001/health
```
Execute verification suite:
```powershell
.\.venv\Scripts\python.exe verify_phase12.py
```
Scorecard must report 22/22 PASS.
