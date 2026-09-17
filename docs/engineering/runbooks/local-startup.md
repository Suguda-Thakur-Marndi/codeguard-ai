# Operational Runbook: Local Development Environment Startup

**Runbook ID**: `RB-OPS-001`  
**Classification**: Standard Operating Procedure  
**Target Services**: API Core, MCP Server, Redis, Frontend Web

---

## 1. Prerequisites

- Python 3.11+ (Python 3.12 or 3.13 recommended)
- Node.js 20+ (Node.js 22 LTS recommended)
- Virtual environment at `.venv`

---

## 2. Step-by-Step Startup Sequence

### Step 1: Environment Variables Setup
Ensure `.env` exists in the repository root (copied from `.env.example`):
```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```
Verify critical variables are set:
- `APP_ENV=development`
- `DATABASE_URL=sqlite:///./codeguard.db` (or PostgreSQL connection string)
- `SECRET_KEY=change-this-to-a-secure-random-secret-key-at-least-32-chars`
- `GITHUB_WEBHOOK_SECRET=development-webhook-secret`

### Step 2: Database Initialization & Migration
Apply all 6 Alembic revisions to establish the 27 required database tables:
```powershell
cd apps/api
..\..\.venv\Scripts\alembic upgrade head
cd ..\..
```

### Step 3: Launch Backend Core API
In Terminal 1:
```powershell
.\.venv\Scripts\uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload
```
Verify API health:
```powershell
curl http://127.0.0.1:8000/api/v1/live
# Expected: {"status":"alive"}
```

### Step 4: Launch MCP Server
In Terminal 2:
```powershell
.\.venv\Scripts\uvicorn app.main:app --app-dir apps/mcp-server --host 127.0.0.1 --port 8001 --reload
```

### Step 5: Launch Next.js Frontend Dashboard
In Terminal 3:
```powershell
cd apps/web
npm run dev
```
Open browser at `http://localhost:3000`.

---

## 3. Verification Checklist

- [ ] `http://localhost:8000/api/v1/health` returns `200 OK`
- [ ] `http://localhost:8001/health` returns `200 OK`
- [ ] Dashboard at `http://localhost:3000` renders pull requests and approval list
