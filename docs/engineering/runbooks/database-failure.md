# Operational Runbook: Relational Database Outage & Recovery

**Runbook ID**: `RB-OPS-004`  
**Classification**: Incident Response / Recovery  
**Target Services**: PostgreSQL / SQLite Database Cluster

---

## 1. Symptoms & Alerts

- **Alert**: `DatabaseConnectionError` / `DatabaseHealthCheckFailed`
- **Symptom**: `/api/v1/health` returns HTTP 503 or `{"database": "unhealthy"}`.
- **Client Behavior**: Ingestion webhooks return HTTP 500 or drop into retry queues.

---

## 2. Immediate Diagnostic Procedure

### Step 1: Check Database Container & Connectivity
```bash
docker compose -f infra/docker/docker-compose.prod.yml ps db
docker compose -f infra/docker/docker-compose.prod.yml logs --tail=100 db
```

### Step 2: Test Direct SQL Connectivity
```bash
docker exec -it codeguard-db pg_isready -U postgres -d codeguard
```

### Step 3: Check Disk Space & Connection Limits
```bash
# Check volume disk space
df -h /var/lib/postgresql/data

# Check active connections
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
```

---

## 3. Recovery Procedure

### Scenario A: Process Stopped / Crashed
```bash
docker compose -f infra/docker/docker-compose.prod.yml restart db
# Verify migrations
docker compose -f infra/docker/docker-compose.prod.yml run --rm api alembic check
```

### Scenario B: Data Corruption / Point-in-Time Restore (PITR)
If the database requires disaster recovery from automated backup:
1. Stop backend services to halt writes:
   ```bash
   docker compose -f infra/docker/docker-compose.prod.yml stop api worker
   ```
2. Restore from latest verified backup snapshot:
   ```bash
   gunzip -c /backups/codeguard_backup_latest.sql.gz | docker exec -i codeguard-db psql -U postgres codeguard
   ```
3. Verify table counts (27 primary tables must exist):
   ```sql
   SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';
   ```
4. Restart API and Worker services:
   ```bash
   docker compose -f infra/docker/docker-compose.prod.yml start api worker
   ```
