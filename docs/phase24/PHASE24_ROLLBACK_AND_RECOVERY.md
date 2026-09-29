# CodeGuard AI — Phase 24: Production Rollback & Disaster Recovery Runbook

**Document ID**: `DOC-P24-ROLLBACK-01`  
**Date**: September 29, 2026  
**Software Version**: `1.0.0`  
**Working Branch**: `main`  
**Base Commit**: `085615eb45da36135a7374b614e3705ad9ca2468`  
**Operational Lead**: Site Reliability Engineer & Security Lead  

---

## 1. Rollback Governance & Stop Conditions

This runbook defines the mandatory, deterministic rollback procedures and disaster recovery protocols for **CodeGuard AI** in production environments.

In the event of an operational failure, security anomaly, or publication defect, the SRE and on-call engineers must immediately trigger rollback upon encountering any of the following **Emergency Rollback Triggers**:

| Trigger ID | Incident Condition | Severity | Immediate Action |
| :--- | :--- | :---: | :--- |
| **TRG-01** | **Data Isolation Breach**: Any observation of repository code, metadata, or review findings crossing tenant boundaries | CRITICAL | Activate Emergency Kill-Switch; halt API; rollback immediately. |
| **TRG-02** | **Secret Leakage**: Any API token, private key, or credential displayed in review comments, dashboard logs, or traces | CRITICAL | Activate Kill-Switch; rotate exposed credentials; rollback. |
| **TRG-03** | **Unreviewed Publication**: Any review comment published to GitHub without verified human approval | HIGH | Set `PUBLISHING_ENABLED=false`; suspend Celery queues. |
| **TRG-04** | **Database Failure**: Alembic migration failure, database deadlock, or connection pool timeout (>30s) | HIGH | Downgrade migration; restore database from snapshot. |
| **TRG-05** | **Service Degradation**: HTTP 5xx error rate > 1.0% or review processing P95 latency > 180s over 5 minutes | MEDIUM | Revert application containers to previous release tag. |

---

## 2. Emergency Kill-Switch Protocol

If an active security or publication incident occurs, execute the **Emergency Kill-Switch** before performing full infrastructure rollback:

```powershell
# ==============================================================================
# EMERGENCY KILL-SWITCH RUNBOOK (< 60 SECONDS TO MITIGATION)
# ==============================================================================

# 1. Instantly silence outgoing GitHub API publication without stopping analysis
# Set environment variable on host or in .env:
#   PUBLISHING_ENABLED=false
docker compose -f docker-compose.prod.yml exec -T api python -c "
from app.core.config import settings
settings.PUBLISHING_ENABLED = False
print('CRITICAL: Outgoing GitHub publication DISABLED')
"

# 2. Halt Celery asynchronous processing workers
docker compose -f docker-compose.prod.yml stop worker

# 3. Flush pending review queue to prevent processing compromised webhooks
docker compose -f docker-compose.prod.yml exec -T redis redis-cli -a "$REDIS_PASSWORD" flushdb

# 4. Revoke or rotate GitHub App webhook secret to reject incoming deliveries
# (Rotate secret in GitHub App settings -> Webhooks -> Secret)
```

---

## 3. Application Container Rollback Procedure

To roll back the CodeGuard AI application cluster to the previously verified stable release:

```powershell
# ==============================================================================
# APPLICATION CONTAINER ROLLBACK RUNBOOK
# ==============================================================================

# STEP 1: Identify previous stable release commit or image tag
PREVIOUS_RELEASE_TAG="0.9.0"  # or previous commit SHA
echo "Rolling back CodeGuard AI to: $PREVIOUS_RELEASE_TAG"

# STEP 2: Gracefully terminate current containers
docker compose -f docker-compose.prod.yml down --timeout 15

# STEP 3: Switch repository / manifest to previous release tag
git checkout "$PREVIOUS_RELEASE_TAG"

# STEP 4: Launch previous container services
docker compose -f docker-compose.prod.yml up -d --force-recreate

# STEP 5: Verify post-rollback service health
curl -f http://localhost:8000/api/v1/live
curl -f http://localhost:8000/api/v1/health
curl -f http://localhost:8001/health
curl -f http://localhost:3000
```

---

## 4. Database Rollback & Point-in-Time Recovery

### 4.1 Schema Migration Rollback (Alembic Downgrade)
If a newly applied database migration caused data corruption or performance regressions:

```powershell
# Check current migration revision
docker compose -f docker-compose.prod.yml run --rm api alembic current

# Downgrade 1 revision step
docker compose -f docker-compose.prod.yml run --rm api alembic downgrade -1

# Verify new current revision
docker compose -f docker-compose.prod.yml run --rm api alembic current
```

### 4.2 Full Database Point-in-Time Restore
If physical database corruption or data loss occurred, restore the database from the pre-deployment backup snapshot:

```powershell
# 1. Stop write traffic by halting API and workers
docker compose -f docker-compose.prod.yml stop api worker

# 2. Execute automated database restore script (verified in AC-BK and verify_phase16 Gate 05)
python scripts/restore_db.py --backup-file backups/pre_deployment_snapshot.sql.gz

# 3. Verify database table schema integrity (assert 27 domain tables present)
docker compose -f docker-compose.prod.yml run --rm api python -c "
from app.db.base import Base
from app.db.session import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f'Restored {len(tables)} tables successfully.')
assert len(tables) >= 27, 'Table count validation failed!'
"

# 4. Restart application services
docker compose -f docker-compose.prod.yml up -d api worker
```

---

## 5. Post-Rollback Validation Checklist

Before declaring the rollback complete and resuming operations, the on-call engineer must verify:

- [ ] All 6 core containers (`postgres`, `redis`, `mcp-server`, `api`, `worker`, `web`) are running and report `healthy`.
- [ ] Database connection pool latency is within normal thresholds (`<10ms`).
- [ ] Redis cache accepts reads and writes without error.
- [ ] GitHub webhook endpoint `/api/v1/webhooks/github` accepts signed payloads and returns HTTP 202.
- [ ] MCP Sentinel server `/tools/list` returns only authorized read-only tools.
- [ ] No unhandled exceptions appear in `docker compose -f docker-compose.prod.yml logs --tail=100 api`.

---

## 6. Incident Follow-Up & Root Cause Analysis (RCA)

Following any production rollback, the engineering team must execute the **Blameless Incident Follow-Up Protocol** (`docs/maintenance/INCIDENT_FOLLOWUP.md`):

1. **Incident Timeline Reconstruction**: Extract correlated logs using `X-Request-ID` and trace identifiers.
2. **Root Cause Analysis (5 Whys)**: Determine the systemic failure mode (e.g., unexpected schema constraint, third-party API timeout, unhandled edge case).
3. **Permanent Regression Test Creation**: Add a targeted regression test reproducing the failure condition in `apps/api/tests/`.
4. **Post-Mortem Publication**: Publish incident post-mortem within 48 hours to `docs/incidents/`.
