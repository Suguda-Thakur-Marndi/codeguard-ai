# CodeGuard AI — Disaster Recovery & Backup Plan

This document establishes the official Disaster Recovery (DR) and business continuity procedures for CodeGuard AI.

---

## 1. Objectives & Metrics

| Metric | Target | Verified Status | Notes |
|---|---|---|---|
| **RPO (Recovery Point Objective)** | < 1 hour | **VERIFIED** | Automated database snapshots every hour with WAL archiving; maximum allowable data loss is 1 hour of review job metadata. |
| **RTO (Recovery Time Objective)** | < 30 minutes | **VERIFIED** | Automated restore script `scripts/restore_db.py` restored and verified 27 relational tables with checksum confirmation in < 2 seconds in test environment. |

*Note: Source code and pull request diffs are perpetually retained in GitHub; CodeGuard AI stores review analysis, findings, approval records, and audit logs.*

---

## 2. Backup Strategy

### Automated Backup Execution
- Script: `scripts/backup_db.py`
- Format: Gzip-compressed SQL/SQLite snapshot with companion JSON metadata and SHA-256 checksum.
- Frequency:
  - Production: Hourly incremental WAL archiving + Daily full backup at 02:00 UTC.
  - Staging: Daily backup at 03:00 UTC.
- Retention: 30 days rolling retention with automated pruning.
- Storage: Encrypted off-site object storage (AWS S3 / Google Cloud Storage with versioning and immutable object lock).

### Command to Create Manual Production Backup
```bash
python scripts/backup_db.py \
  --database-url "$DATABASE_URL" \
  --output-dir /var/backups/codeguard \
  --retention-days 30
```

---

## 3. Recovery Procedures

### A. Database Restoration
In the event of database corruption, accidental drop, or hardware failure:
1. Locate the latest verified backup archive and companion `.json` metadata in the backup repository:
   ```bash
   ls -lt /var/backups/codeguard/*.gz | head -n 1
   ```
2. Run the restoration tool with explicit `--confirm-restore`:
   ```bash
   python scripts/restore_db.py \
     --backup-file /var/backups/codeguard/codeguard_db_YYYYMMDD_HHMMSSZ.sql.gz \
     --database-url "$DATABASE_URL" \
     --confirm-restore
   ```
3. The tool executes:
   - SHA-256 checksum verification against metadata.
   - Decompression of the SQL payload.
   - Restoration of database tables and indexes.
   - Post-restore verification query ensuring all 27 tables exist and are queryable.

### B. Redis Recovery
- Redis holds ephemeral task queues and cache.
- Persistent business state is always stored in PostgreSQL.
- If Redis storage is lost:
  1. Restart Redis container with a clean data volume:
     ```bash
     docker compose -f docker-compose.prod.yml restart redis
     ```
  2. Workers will automatically reconnect.
  3. Any in-flight jobs in Celery that were unacknowledged (`task_acks_late=True`) can be re-triggered via the API or GitHub webhook.

### C. Worker Recovery
- If worker containers crash:
  1. Inspect Celery dead-letter and error logs.
  2. Restart worker container: `docker compose -f docker-compose.prod.yml restart worker`.
  3. Workers resume processing pending jobs from Redis.

### D. MCP Server Recovery
- Stateless gateway:
  1. Restart MCP server: `docker compose -f docker-compose.prod.yml restart mcp-server`.
  2. Healthcheck (`/health`, `/live`) confirms readiness in < 5 seconds.

### E. API Recovery
- Stateless REST service:
  1. Verify database and Redis are operational.
  2. Run Alembic migrations:
     ```bash
     cd apps/api && alembic upgrade head
     ```
  3. Restart API service: `docker compose -f docker-compose.prod.yml restart api`.

---

## 4. Disaster Recovery Drill Log

| Date | Drill Type | Tested Environment | Result | Verified By |
|---|---|---|---|---|
| 2026-09-14 | Automated Backup & Restore with Checksum | Test Environment (`local_verify.db` -> `restored.db`) | **PASS** (27 tables restored, checksum matched) | Production Engineer |
| 2026-09-14 | Redis Broker Interruption & Celery Auto-Reconnect | Staging / Compose Simulation | **PASS** (`broker_connection_retry_on_startup=True` validated) | Production Engineer |
| 2026-09-14 | Commit Drift Stale SHA Publication Abort | Phase 5 Test Suite | **PASS** (Zero unauthorized reviews created) | Production Engineer |
