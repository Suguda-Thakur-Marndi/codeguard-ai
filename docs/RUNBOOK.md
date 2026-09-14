# CodeGuard AI — Production Operations Runbook

This runbook outlines operational procedures for diagnosing, resolving, and verifying system incidents across the CodeGuard AI platform.

---

## Service Overview & Key Ports

| Component | Port | Health Endpoint | Log Indicator |
|---|---|---|---|
| **API Server** | 8000 | `/api/v1/health`, `/api/v1/live`, `/api/v1/ready` | `event="http_request_completed"` |
| **Worker (Celery)** | - | Redis heartbeat | `event="review_job_started"`, `event="review_job_completed"` |
| **MCP Server** | 8001 | `/health`, `/live`, `/ready` | `event="mcp_tool_execution"` |
| **Frontend Dashboard** | 3000 | `/` (HTTP 200) | Next.js server logs |
| **PostgreSQL** | 5432 | `pg_isready -U codeguard` | PostgreSQL transaction logs |
| **Redis** | 6379 | `redis-cli ping` | Redis persistence logs |

---

## Standard Incident Procedures

### 1. API Server Down or Unresponsive
- **Symptom**: HTTP 502/503/504 errors on `/api/v1/*`, container restart loops, alerts firing on API process availability.
- **Diagnosis**:
  1. Check process status: `docker ps -f name=codeguard-api`
  2. Inspect container logs: `docker logs --tail 200 codeguard-api`
  3. Check liveness and readiness:
     ```bash
     curl -i http://localhost:8000/api/v1/live
     curl -i http://localhost:8000/api/v1/ready
     ```
  4. If `/ready` returns HTTP 503, inspect PostgreSQL or Redis connectivity fields in the response.
- **Safe Action**:
  1. If memory exhaustion / OOM is detected, increase memory limits in `docker-compose.prod.yml`.
  2. If process hung on database pool exhaustion, check active DB connections:
     ```sql
     SELECT count(*), state FROM pg_stat_activity GROUP BY state;
     ```
  3. Restart API service gracefully:
     ```bash
     docker compose -f docker-compose.prod.yml restart api
     ```
- **Verification**: `curl -f http://localhost:8000/api/v1/live` returns HTTP 200 `{"status": "ok"}`.

---

### 2. Worker Down or Review Queue Backlog
- **Symptom**: Pull requests receive webhooks (HTTP 202), but review jobs remain in `PENDING` or `PROCESSING` indefinitely; Celery queue depth grows.
- **Diagnosis**:
  1. Check Celery queue backlog in Redis:
     ```bash
     docker exec codeguard-redis redis-cli -a "$REDIS_PASSWORD" llen celery
     ```
  2. Inspect worker logs: `docker logs --tail 200 codeguard-worker`
  3. Verify Celery worker process: `docker exec codeguard-worker celery -A app.workers.celery_app inspect ping`
- **Safe Action**:
  1. If queue is stuck due to deadlocked worker sub-process, restart worker service:
     ```bash
     docker compose -f docker-compose.prod.yml restart worker
     ```
  2. If queue backlog is high under traffic burst, scale worker concurrency:
     ```bash
     docker compose -f docker-compose.prod.yml up -d --scale worker=4
     ```
- **Verification**: Queue depth drains to 0; jobs transition from `PROCESSING` to `COMPLETED`.

---

### 3. Database Unavailable or Connection Pool Exhaustion
- **Symptom**: API logs show `OperationalError: connection to server lost` or `TimeoutError: QueuePool limit exceeded`.
- **Diagnosis**:
  1. Test PostgreSQL connectivity: `docker exec codeguard-postgres pg_isready -U codeguard`
  2. Check connection limits:
     ```sql
     SHOW max_connections;
     SELECT count(*) FROM pg_stat_activity;
     ```
- **Safe Action**:
  1. Terminate idle in transaction connections:
     ```sql
     SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < now() - interval '5 minutes';
     ```
  2. If PostgreSQL container is stopped, inspect disk space before restarting:
     ```bash
     df -h
     docker compose -f docker-compose.prod.yml restart postgres
     ```
- **Verification**: `curl http://localhost:8000/api/v1/ready` returns `{"status": "ready", "postgres": "connected"}`.

---

### 4. Redis Unavailable or Broker Connection Refused
- **Symptom**: Worker exits on startup, API returns HTTP 503 on `/ready`, webhook ingestion logs error queuing Celery task.
- **Diagnosis**:
  1. Check Redis process: `docker exec codeguard-redis redis-cli -a "$REDIS_PASSWORD" ping`
  2. Check memory usage: `docker exec codeguard-redis redis-cli -a "$REDIS_PASSWORD" info memory`
- **Safe Action**:
  1. Restart Redis container:
     ```bash
     docker compose -f docker-compose.prod.yml restart redis
     ```
  2. Verify Celery reconnects automatically (`broker_connection_retry_on_startup=True`).
- **Verification**: `curl http://localhost:8000/api/v1/ready` returns `{"redis": "connected"}`.

---

### 5. Gemini AI API Unavailable, Rate-Limited, or Timeout
- **Symptom**: Review jobs fail with `LLMProviderError`, `GeminiAPIError`, HTTP 429 Too Many Requests, or timeouts exceeding 60s.
- **Diagnosis**:
  1. Check Google AI Studio / Cloud status dashboard.
  2. Inspect API logs for quota or rate limit messages:
     ```bash
     docker logs codeguard-worker | grep -i "rate_limit\|quota\|gemini"
     ```
- **Safe Action**:
  1. Verify token quota and tier in Google Cloud Console.
  2. Transient 429: Celery worker automatically backs off with exponential jitter.
  3. If primary model tier (`gemini-2.5-pro`) is degraded, switch reasoning tier to fast model (`gemini-2.5-flash`) via environment variable:
     ```env
     MODEL_TIER_SECURITY=fast
     MODEL_TIER_BUG=fast
     ```
  4. The system reports honest degraded status without generating fake findings.
- **Verification**: Review jobs complete with verified findings and recorded token costs.

---

### 6. GitHub API Rate Limit or Webhook Ingestion Failure
- **Symptom**: Webhook ingestion returns HTTP 400 (signature error) or reviews fail with `GitHubAPIError: 403 rate limit exceeded`.
- **Diagnosis**:
  1. Check rate limits via GitHub App installation token:
     ```bash
     curl -H "Authorization: Bearer $INSTALLATION_TOKEN" https://api.github.com/rate_limit
     ```
  2. If signature verification fails, check if `GITHUB_WEBHOOK_SECRET` matches repository configuration.
- **Safe Action**:
  1. For rate limits, the worker automatically defers retryable tasks (`autoretry_for=(GitHubAPIError,)`).
  2. Verify GitHub App is granted minimum required permissions (Pull requests: Read & Write).
- **Verification**: GitHub rate limit reset timestamp passes; webhook returns HTTP 202 `{"status": "accepted"}`.

---

### 7. Stale SHA Detected During Publication
- **Symptom**: Human reviewer clicks Approve, but publication status is marked `STALE` with zero reviews published to GitHub.
- **Diagnosis**:
  1. Inspect publication error message: `PR HEAD SHA mismatch: verified on abc12345, but PR HEAD is now def67890`.
  2. This is the **correct, intended security behavior**: a developer pushed new commits to the PR after the review was generated.
- **Safe Action**:
  1. Inform the developer and reviewer that the PR HEAD has advanced.
  2. The webhook automatically triggers a new review job for the latest commit SHA.
  3. Review findings must be re-validated on the new commit SHA before publication.
- **Verification**: The new review job completes, creating an approval request bound to the new HEAD SHA.

---

### 8. Sandbox Timeout or Resource Limit Exceeded
- **Symptom**: Verification logs report `ValidationResultData(status="TIMEOUT")` or process limit hit.
- **Diagnosis**:
  1. Inspect scenario execution logs: check if user test suite contained an infinite loop or high memory allocation.
  2. Confirm container limits enforced: CPU limit (1.0), memory (512M), processes (64), timeout (30s).
- **Safe Action**:
  1. Adversarial Judge automatically treats timeout as behavioral validation failure.
  2. Ensure orphaned sandbox containers are cleaned up (`docker ps -a -f ancestor=codeguard-sandbox:latest`).
- **Verification**: Sandbox container exits cleanly with zero leaked resources on host.

---

### 9. High AI Token Costs or Runaway Review Loops
- **Symptom**: Daily AI expenditure spikes above configured threshold; token consumption exceeds budget.
- **Diagnosis**:
  1. Query token metrics in database:
     ```sql
     SELECT sum(input_tokens), sum(output_tokens), sum(estimated_cost) FROM agent_runs WHERE created_at > now() - interval '24 hours';
     ```
  2. Identify high-cost review jobs or large pull request diffs.
- **Safe Action**:
  1. Enforce strict context size boundaries:
     ```env
     MAX_CONTEXT_CHARS=16000
     MAX_CONTEXT_FILES=10
     MAX_CONTEXT_SYMBOLS=30
     ```
  2. Ignore draft pull requests: `IGNORE_DRAFT_PRS=true`.
- **Verification**: Average token count per review remains within 25,000–45,000 tokens.
