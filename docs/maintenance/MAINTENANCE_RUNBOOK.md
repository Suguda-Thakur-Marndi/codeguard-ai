# CodeGuard AI — Engineering Maintenance Runbook

This runbook documents actionable procedures and verified commands for maintaining, operating, and releasing CodeGuard AI.

---

## 1. Updating Dependencies

### 1.1 Python Dependencies (`apps/api`, `apps/mcp-server`, `packages/code-intelligence`)
```bash
# 1. Activate virtual environment
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# 2. Inspect outdated packages
pip list --outdated

# 3. Update specific package in target pyproject.toml
# Edit apps/api/pyproject.toml (e.g. update fastapi version)

# 4. Reinstall editable packages in active virtualenv
pip install -e "./packages/code-intelligence" -e "./apps/api[dev]" -e "./apps/mcp-server"

# 5. Run linting and test suites
ruff check .
pytest apps/api/tests apps/mcp-server/tests
python benchmark.py regression --baseline benchmark_report.json
```

### 1.2 Frontend Dependencies (`apps/web`)
```bash
cd apps/web

# 1. Check outdated npm packages
npm outdated

# 2. Update specific package
npm install <package-name>@latest

# 3. Run type checking and build verification
npm run lint
npm run build
```

---

## 2. Updating Database Schema (Alembic)

```bash
# 1. Create a new migration revision
cd apps/api
alembic revision -m "add_column_name_to_table"

# 2. Edit the generated file in apps/api/alembic/versions/
# Implement both upgrade() and downgrade() functions following expand-and-contract pattern.

# 3. Test upgrade against local database
alembic upgrade head

# 4. Test downgrade rollback
alembic downgrade -1

# 5. Return to head
alembic upgrade head

# 6. Run operational migration gate
cd ../..
python verify_phase16.py
```

---

## 3. Updating AI Model Configuration & Prompts

### 3.1 Model Configuration Update
```bash
# 1. Edit apps/api/app/core/config.py to update default model names
# Or configure via environment variables:
# export GEMINI_MODEL_PRO="gemini-1.5-pro-002"
# export GEMINI_MODEL_FLASH="gemini-1.5-flash-002"

# 2. Validate benchmark scenario ground truth
python benchmark.py validate

# 3. Execute candidate benchmark run
python benchmark.py run --dataset v1 --name candidate-model-eval --export-json candidate_report.json

# 4. Run regression detection against active baseline
python benchmark.py regression --baseline benchmark_report.json --candidate candidate_report.json
```

### 3.2 Prompt Template Update
```bash
# 1. Edit prompt templates in apps/api/app/services/agent_orchestrator.py
# 2. Increment prompt version constant and update SHA-256 digest
# 3. Run targeted agent tests
pytest apps/api/tests/test_agents.py apps/api/tests/test_orchestrator.py
# 4. Run benchmark regression
python benchmark.py regression --baseline benchmark_report.json
```

---

## 4. Authoring Permanent Regression Tests

Whenever a bug is fixed or invariant reinforced, add a permanent test to `apps/api/tests/test_invariants_phase17.py`:

```bash
# 1. Open apps/api/tests/test_invariants_phase17.py
# 2. Author a test using pytest syntax and standard fixtures (test_client, db_session)
# 3. Verify test fails before bugfix, passes after bugfix
pytest apps/api/tests/test_invariants_phase17.py -k test_my_invariant -v
```

---

## 5. Investigating CI Pipeline Failures

```bash
# 1. Reproduce Step 1 (Lint) locally:
ruff check .

# 2. Reproduce Step 2 (Pytest & Benchmarks) locally:
pytest apps/api/tests -v
pytest apps/mcp-server/tests -o pythonpath=apps/mcp-server -v
python benchmark.py validate
python benchmark.py regression --baseline benchmark_report.json

# 3. Reproduce Step 3 (Frontend Build) locally:
cd apps/web
npm run lint
npm run build
cd ../..
```

---

## 6. Investigating Production Errors & Alerts

```bash
# 1. Extract recent error logs filtered by correlation ID or error level
# (From local run or Docker container logs)
# Linux / Docker:
docker logs codeguard-api-1 --since 1h | grep -E "ERROR|CRITICAL"

# 2. Trace request by request_id:
grep "req-9e94d8d0-6dfb-4153-bb50-4e1437a4d8a2" apps/api/logs/*.log

# 3. Inspect Redis queue backlog:
redis-cli -h localhost -p 6379 LLEN celery

# 4. Check API health and readiness:
curl -i http://localhost:8000/api/v1/health
curl -i http://localhost:8000/api/v1/ready
```

---

## 7. Release & Deployment Procedure

```bash
# STEP 1: Verify all 27 Master Operational Gates
python verify_phase16.py

# STEP 2: Verify Master Acceptance Suite (36/36 scenarios)
python scripts/run_acceptance_suite.py

# STEP 3: Verify Zero Git Working Tree Drift
git status -s

# STEP 4: Build Frontend Assets
cd apps/web && npm run build && cd ../..

# STEP 5: Tag Release Commit
git tag -a v0.1.0 -m "Release v0.1.0: Production verified baseline"
git push origin v0.1.0

# STEP 6: Apply Database Migrations on Staging
alembic upgrade head

# STEP 7: Verify Staging Health Endpoints
curl -f https://dashboard-staging.codeguard.internal/api/v1/health
curl -f https://dashboard-staging.codeguard.internal/api/v1/ready

# STEP 8: Promote to Production (Triggered via GitHub Actions Release Gate)
```

---

## 8. Rollback Procedure

If a production deployment encounters elevated error rates, latency surges, or health probe failures:

```bash
# STEP 1: Rollback Container Deployments
# In Kubernetes / Cloud deployment:
kubectl rollout undo deployment/codeguard-api -n codeguard-prod
kubectl rollout undo deployment/codeguard-web -n codeguard-prod
kubectl rollout undo deployment/codeguard-worker -n codeguard-prod

# STEP 2: Rollback Database Schema (if backward-incompatible migration was deployed)
cd apps/api
alembic downgrade -1

# STEP 3: Verify Health Restoration
curl -f https://api.codeguard.ai/api/v1/health
curl -f https://api.codeguard.ai/api/v1/ready

# STEP 4: Log Incident & Trigger Post-Mortem
# Follow docs/maintenance/INCIDENT_FOLLOWUP.md
```
