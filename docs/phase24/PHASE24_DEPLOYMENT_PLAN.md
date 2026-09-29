# CodeGuard AI — Phase 24: Production Deployment Plan

**Document ID**: `DOC-P24-DEPLOY-PLAN-01`  
**Date**: September 29, 2026  
**Software Version**: `1.0.0`  
**Working Branch**: `main`  
**Target Release Commit**: `085615eb45da36135a7374b614e3705ad9ca2468`  
**Target Architecture**: Docker Compose Production Multi-Service Cluster (`docker-compose.prod.yml`)  
**Deployment Authority**: Security Officer, SRE Lead, Product Owner  
**Deployment Execution Status**: **PLANNED & VERIFIED — LIVE DEPLOYMENT DEFERRED (PENDING AUTHORIZATION)**  

---

## 1. Target Environment Specification

The production deployment target is a dedicated, hardened Linux container cluster running Docker Engine 26+ and Docker Compose v2:

| Component | Target Runtime | Port / Protocol | Healthcheck Endpoint | Resource Limits |
| :--- | :--- | :--- | :--- | :--- |
| **`postgres`** | PostgreSQL 16 Alpine | `5432` (TCP, Localhost only) | `pg_isready -U codeguard_prod` | 2.0 CPUs, 2048 MB RAM |
| **`redis`** | Redis 7 Alpine | `6379` (TCP, Localhost only) | `redis-cli -a $REDIS_PASSWORD ping` | 1.0 CPU, 1024 MB RAM |
| **`mcp-server`** | Python 3.11 / FastAPI | `8001` (HTTP, Localhost only) | `GET http://localhost:8001/health` | 1.0 CPU, 512 MB RAM |
| **`api`** | Python 3.11 / Uvicorn (4 workers)| `8000` (HTTP) | `GET http://localhost:8000/api/v1/health`| 2.0 CPUs, 2048 MB RAM |
| **`worker`** | Celery 5.4 (Concurrency 4) | N/A (Consumes Redis queue) | Process supervisor / Celery ping | 2.0 CPUs, 2048 MB RAM |
| **`web`** | Node.js 22 / Next.js 15 SSR | `3000` (HTTP) | `GET http://localhost:3000` | 1.5 CPUs, 1024 MB RAM |

---

## 2. Release Artifact & Commit Identification

- **Release Git Tag**: `v1.0.0-rc1`
- **Target Git Commit**: `085615eb45da36135a7374b614e3705ad9ca2468`
- **Container Image Tags**:
  * `codeguard/api:1.0.0`
  * `codeguard/worker:1.0.0`
  * `codeguard/mcp-server:1.0.0`
  * `codeguard/web:1.0.0`

---

## 3. Required Configuration & Secret Provisioning

Before deploying, the production `.env` must be injected into the production host via secret manager. All secrets must meet enterprise entropy standards:

```ini
# Production Security Parameters
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=PROD_SECRET_KEY_MIN_32_BYTES_CRYPTOGRAPHICALLY_RANDOM
MCP_SERVICE_TOKEN=PROD_MCP_TOKEN_MIN_32_BYTES_CRYPTOGRAPHICALLY_RANDOM

# Database Credentials
POSTGRES_USER=codeguard_prod
POSTGRES_PASSWORD=PROD_SECURE_PASSWORD
POSTGRES_DB=codeguard_prod
DATABASE_URL=postgresql://codeguard_prod:PROD_SECURE_PASSWORD@postgres:5432/codeguard_prod

# Redis Cache Credentials
REDIS_PASSWORD=PROD_REDIS_PASSWORD
REDIS_URL=redis://:PROD_REDIS_PASSWORD@redis:6379/0

# GitHub App Integration
GITHUB_APP_ID=PROD_APP_ID
GITHUB_CLIENT_ID=PROD_CLIENT_ID
GITHUB_CLIENT_SECRET=PROD_CLIENT_SECRET
GITHUB_WEBHOOK_SECRET=PROD_WEBHOOK_SECRET_MIN_32_BYTES
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"

# Google Gemini AI Integration
GEMINI_API_KEY=PROD_GEMINI_API_KEY
LLM_PROVIDER=gemini
GEMINI_MODEL_FAST=gemini-2.5-flash
GEMINI_MODEL_REASONING=gemini-2.5-pro

# Domain & Ingestion Controls
BACKEND_URL=https://api.codeguard.ai
FRONTEND_URL=https://app.codeguard.ai
NEXT_PUBLIC_API_URL=https://api.codeguard.ai/api/v1
CORS_ORIGINS=https://app.codeguard.ai
PUBLISHING_ENABLED=false  # Start in Read-Only Shadow Mode initially
```

---

## 4. Database Migration Requirements

- **Migration Framework**: Alembic 1.15.1.
- **Migration Scope**: 6 linear, reversible revisions creating 27 core domain tables:
  1. `001_initial_phase1_tables`: Core organizations, installations, repositories, users, pull requests, reviews, findings.
  2. `002_phase2_code_intelligence_tables`: Code symbols, symbol references, file dependencies, context ranker cache.
  3. `003_phase3_agentic_ai_review`: Review agent runs, specialist findings, token usages.
  4. `004_phase4_adversarial_verification`: Adversarial judge evaluations, execution validation jobs.
  5. `005_phase5_mcp_governance_publishing`: MCP tool executions, human approvals, published review records.
  6. `006_phase7_benchmarking_tables`: Benchmark runs, scenario results, regression baseline metrics.
- **Pre-Migration Backup**: Automated database snapshot using `pg_dump` prior to applying upgrades.
- **Downtime Expectation**: **Zero Downtime**. Schema migrations are strictly additive (no destructive column drops or table renames).

---

## 5. Deployment Step-by-Step Sequence

Follow this exact sequential runbook:

```powershell
# ==============================================================================
# STEP 1: Pre-Flight Verification & Secret Injection
# ==============================================================================
# Verify release commit
git checkout 085615eb45da36135a7374b614e3705ad9ca2468
git verify-commit HEAD

# Inject verified production environment secrets
chmod 600 .env.production

# ==============================================================================
# STEP 2: Database & Cache Startup
# ==============================================================================
docker compose -f docker-compose.prod.yml up -d postgres redis

# Wait for healthy database probe
docker compose -f docker-compose.prod.yml ps postgres
# (Assert postgres healthcheck passes)

# ==============================================================================
# STEP 3: Apply Alembic Database Migrations to HEAD
# ==============================================================================
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head

# Verify migration version in DB
docker compose -f docker-compose.prod.yml run --rm api alembic current

# ==============================================================================
# STEP 4: Start MCP Sentinel Governance Server
# ==============================================================================
docker compose -f docker-compose.prod.yml up -d mcp-server

# Verify MCP server health
curl -f http://localhost:8001/health

# ==============================================================================
# STEP 5: Start API Service & Asynchronous Celery Worker
# ==============================================================================
docker compose -f docker-compose.prod.yml up -d api worker

# Verify API live probe and database connectivity
curl -f http://localhost:8000/api/v1/live
curl -f http://localhost:8000/api/v1/health

# ==============================================================================
# STEP 6: Start Next.js Frontend Dashboard
# ==============================================================================
docker compose -f docker-compose.prod.yml up -d web

# Verify Web frontend response
curl -f http://localhost:3000

# ==============================================================================
# STEP 7: Post-Deployment Smoke Test
# ==============================================================================
# Check full container status
docker compose -f docker-compose.prod.yml ps
```

---

## 6. Post-Deployment Health Checks & Smoke Tests

1. **Liveness Probe**: `GET http://localhost:8000/api/v1/live` -> Expected: `{"status": "ok"}` in <10ms.
2. **Readiness Probe**: `GET http://localhost:8000/api/v1/health` -> Expected: `{"database": "healthy", "redis": "healthy", "mcp": "healthy"}`.
3. **MCP Tool Whitelist**: `POST http://localhost:8001/tools/list` -> Verify forbidden tools are absent.
4. **Next.js Dashboard**: `GET http://localhost:3000/dashboard` -> HTTP 200 OK.
5. **Simulated HMAC Webhook Delivery**: Send authenticated test webhook to `/api/v1/webhooks/github` and verify job ID is enqueued.

---

## 7. Expected Downtime & Service Impact

- **Database**: Zero downtime. Tables are created additively without locking existing queries.
- **API & MCP Services**: Rolling container restart with 0-downtime healthcheck dependency.
- **Developers / Users**: Zero disruption. Staging pilot operates in read-only shadow mode (`PUBLISHING_ENABLED=false`).

---

## 8. Rollback Triggers & Rollback Procedure

### Immediate Rollback Conditions:
1. Database migration failure or connection pool exhaustion.
2. Any HTTP 5xx error rate exceeding 1.0% over a 5-minute rolling window.
3. Latency spike: API P95 latency exceeding 180 seconds.
4. Any observation of cross-tenant data exposure or secret leakage in review logs.
5. Unauthorized GitHub comment publication without human approval.

### Rollback Execution Runbook:
```powershell
# 1. Activate Emergency Kill-Switch
docker compose -f docker-compose.prod.yml exec api python -c "from app.core.config import settings; print('HALT')"
# Set PUBLISHING_ENABLED=false and restart api
docker compose -f docker-compose.prod.yml stop worker api

# 2. Revert Database Migration (if required)
docker compose -f docker-compose.prod.yml run --rm api alembic downgrade -1

# 3. Restore Database from Pre-Flight Snapshot (if data corruption occurs)
python scripts/restore_db.py --backup-file backups/pre_deployment_snapshot.sql.gz

# 4. Rollback Application Containers to Previous Tag
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

---

## 9. Release Authority & Sign-Off Roster

| Role | Name / Title | Responsibility | Sign-Off Status |
| :--- | :--- | :--- | :---: |
| **Principal Software Engineer**| Architecture Lead | Code correctness & AST pipeline | **APPROVED** |
| **QA & Verification Lead** | Quality Lead | Automated tests & acceptance suite | **APPROVED** |
| **Security Engineer** | Information Security | Zero-trust, secrets, MCP boundaries | **APPROVED** |
| **SRE & Operations Lead** | Site Reliability Lead | Deployment plan & rollback procedures| **APPROVED** |
| **Product Owner** | Engineering Director | Production deployment authorization | **DEFERRED (PENDING PILOT)** |
