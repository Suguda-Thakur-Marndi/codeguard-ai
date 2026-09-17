# Operational Runbook: GitHub API Integration & Rate Limit Outage

**Runbook ID**: `RB-OPS-006`  
**Classification**: External Integration Incident  
**Target Services**: GitHub Webhook Ingest, GitHub Review Publisher (`apps/api/app/github/`)

---

## 1. Symptoms & Failure Modes

- **HTTP 401 / 403 (Authentication Error)**: GitHub App installation token expired or invalid private key.
- **HTTP 429 / Secondary Rate Limits**: GitHub API rate limits exceeded (5,000 requests/hour per installation).
- **HTTP 502 / 503 (GitHub Down)**: Upstream GitHub outages.
- **HTTP 422 (Unprocessable Entity)**: Diff position shifted between diff generation and publication.

---

## 2. Diagnostic Procedure

### Step 1: Inspect Failed Publications Table
```sql
SELECT id, review_job_id, status, error_message, attempt_count, created_at 
FROM github_review_publications 
WHERE status = 'FAILED' OR status = 'RETRYING' 
ORDER BY created_at DESC LIMIT 10;
```

### Step 2: Check GitHub API Rate Limit Status
Query GitHub rate limit using active app installation token:
```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/rate_limit
```

---

## 3. Mitigation & Recovery Steps

### Scenario A: HTTP 429 Rate Limit
- CodeGuard AI automatically reads `Retry-After` and `x-ratelimit-reset` headers and backs off exponentially.
- If persistent, increase token pool by rotating or scaling GitHub App installations across repositories.

### Scenario B: HTTP 502 / 503 Upstream Outage
- Retries are automatically scheduled by Celery with jitter up to 3 attempts.
- If GitHub remains down > 1 hour, trigger batch republish once GitHub status reports operational:
```powershell
.\.venv\Scripts\python.exe scripts/republish_pending_reviews.py
```

### Scenario C: HTTP 422 Invalid Diff Line Position
- Occurs when the target line has drifted or was deleted.
- CodeGuard AI automatically catches 422 errors and republishes the finding as a top-level general review comment rather than crashing the review publication.
