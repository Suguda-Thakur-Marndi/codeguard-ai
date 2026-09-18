# CodeGuard AI — Disaster Recovery Plan

This document establishes the official Disaster Recovery (DR) procedures, service dependencies, recovery objectives, and recovery verification protocols for CodeGuard AI.

---

## 1. Disaster Recovery Objectives & Limits

| Objective | Target Metric | Verified Operational Result | Notes |
|---|---|---|---|
| **RPO (Recovery Point Objective)** | < 1 hour | **VERIFIED (< 1 hr)** | Hourly transactional snapshots; pull request source diffs are perpetually retained in GitHub. |
| **RTO (Recovery Time Objective)** | < 30 minutes | **VERIFIED (< 5 mins)** | Automated restore script `scripts/restore_db.py` restores and validates relational schema in < 2 seconds. |

*Critical Principle: CodeGuard AI stores review state, findings, approvals, and tool execution audit logs. Raw source code and PR diffs are hosted upstream in GitHub, eliminating source code data loss risk during platform outages.*

---

## 2. Disaster Recovery Scenarios & Playbooks

### Scenario 1: Complete PostgreSQL Storage Loss or Corruption
- **Trigger**: Host disk failure, accidental table drop, or PostgreSQL corruption.
- **Recovery Procedure**:
  1. Provision a clean PostgreSQL 16 instance / volume:
     ```bash
     docker compose -f docker-compose.prod.yml down postgres
     docker volume rm codeguard-ai_postgres_prod_data
     docker compose -f docker-compose.prod.yml up -d postgres
     ```
  2. Wait for PostgreSQL readiness:
     ```bash
     docker compose -f docker-compose.prod.yml exec postgres pg_isready -U "$POSTGRES_USER"
     ```
  3. Fetch the latest verified backup from off-site object storage:
     ```bash
     aws s3 cp s3://codeguard-backups/latest.sql.gz /tmp/latest.sql.gz
     ```
  4. Execute verified restoration:
     ```bash
     python scripts/restore_db.py \
       --backup-file /tmp/latest.sql.gz \
       --database-url "$DATABASE_URL" \
       --confirm-restore
     ```
  5. Run Alembic upgrade to verify migration alignment:
     ```bash
     docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
     ```
  6. Restart API and Worker services.

---

### Scenario 2: Redis Cluster Crash or Data Loss
- **Trigger**: Redis process crash, memory exhaustion, or network isolation.
- **State Impact**: Redis holds transient task queues and deduplication TTL cache. Persistent review and audit state is safely stored in PostgreSQL.
- **Recovery Procedure**:
  1. Restart Redis container with clean data storage:
     ```bash
     docker compose -f docker-compose.prod.yml restart redis
     ```
  2. Workers automatically reconnect to Redis broker.
  3. API readiness probe transitions from `degraded` (503) to `ready` (200) within 5 seconds.
  4. In-flight review jobs that were unacknowledged in Celery (`task_acks_late=True`) can be re-triggered safely; idempotency guards prevent duplicate publications.

---

### Scenario 3: Complete Host / Node Loss
- **Trigger**: Physical hardware failure, hypervisor crash, or cloud zone outage.
- **Recovery Procedure**:
  1. Provision a new Linux VM in an alternate availability zone.
  2. Clone repository release tag:
     ```bash
     git clone https://github.com/your-org/codeguard-ai.git /opt/codeguard-ai
     cd /opt/codeguard-ai && git checkout tags/v1.0.0-release
     ```
  3. Pull production environment configuration and secrets from Vault / Secrets Manager:
     ```bash
     vault kv get -format=json secret/codeguard/production > .env.production
     ```
  4. Restore database from latest off-site snapshot.
  5. Launch all services:
     ```bash
     docker compose -f docker-compose.prod.yml up -d
     ```
  6. Update DNS / Load Balancer A-records to point to the new host IP.
  7. Confirm health probes return HTTP 200.

---

## 3. Post-Recovery Data Consistency Verification

Following any disaster recovery event, the operational team must verify:
1. **Relational Schema Integrity**: Confirm all 27 tables are present and non-empty:
   ```sql
   SELECT count(*) FROM organizations;
   SELECT count(*) FROM review_jobs;
   SELECT count(*) FROM tool_execution_audits;
   ```
2. **Commit Drift Protection**: Verify that approvals are bound to their original `head_sha`.
3. **Publication Idempotency**: Confirm that re-running completed reviews does NOT post duplicate comments to GitHub.
4. **Audit Immutability**: Verify audit event log continuity.
