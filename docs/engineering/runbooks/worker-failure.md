# Operational Runbook: Celery Worker Process Failure & Recovery

**Runbook ID**: `RB-OPS-003`  
**Classification**: Incident Response / Recovery  
**Target Services**: Celery Worker Daemon (`apps/api/app/worker.py`), Redis Broker

---

## 1. Symptoms & Alerts

- **Alert**: `CeleryWorkerDown` or `QueueBacklogSpike`
- **Symptom**: Review jobs remain in `PENDING` state for > 60 seconds without transitioning to `RUNNING`.
- **Database Telemetry**: `SELECT count(*) FROM review_jobs WHERE status = 'PENDING' AND created_at < NOW() - INTERVAL '5 minutes';` returns > 0.

---

## 2. Immediate Diagnostic Procedure

### Step 1: Check Worker Container / Process Status
```bash
docker compose -f infra/docker/docker-compose.prod.yml ps worker
docker compose -f infra/docker/docker-compose.prod.yml logs --tail=100 worker
```

### Step 2: Inspect Redis Queue Depth
```bash
docker exec -it codeguard-redis redis-cli -a $REDIS_PASSWORD LLEN celery
```

### Step 3: Identify Root Cause
- **Out of Memory (OOM)**: Kernel `dmesg -T | grep -i oom` indicates worker killed by OOM killer due to giant diff or runaway AST chunking.
- **Unhandled Exception**: Inspect tracebacks in worker logs for unhandled external API exceptions.

---

## 3. Recovery Procedure

### Step 1: Restart Failed Worker
```bash
docker compose -f infra/docker/docker-compose.prod.yml restart worker
```

### Step 2: Clear Stale Locks & Transition Interrupted Jobs
Any jobs interrupted mid-execution (`RUNNING` state during crash) must be recovered:
```sql
UPDATE review_jobs 
SET status = 'FAILED', 
    error_message = 'Worker process terminated unexpectedly; job failed safely'
WHERE status = 'RUNNING' AND updated_at < NOW() - INTERVAL '10 minutes';
```

### Step 3: Re-trigger Interrupted Review Jobs
Users or automated webhooks can re-deliver the PR synchronize event, which will safely re-enter the `PENDING` queue.
