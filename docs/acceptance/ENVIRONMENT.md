# CodeGuard AI — Acceptance Environment Specification

**Document Version**: 1.0.0  
**Phase**: Final Acceptance & Production Simulation

---

## 1. Conceptual Environments

To enforce the Prime Directive and prevent accidental modifications to external systems, CodeGuard AI defines three distinct conceptual environments:

```
┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
│       DEVELOPMENT       │       │         STAGING         │       │       PRODUCTION        │
│   (Local dev machine)   │ ----> │  (Acceptance Sandbox)   │ ----> │    (Live Production)    │
│  - Dev bypass auth      │       │  - Dedicated test DB    │       │  - Zero mock policy     │
│  - Ephemeral SQLite     │       │  - Simulated queues     │       │  - Enforced JWT & roles │
│  - In-memory fallback   │       │  - Strict test schemas  │       │  - Live external APIs   │
└─────────────────────────┘       └─────────────────────────┘       └─────────────────────────┘
```

For the Final Acceptance Phase, all operations execute within a **dedicated staging environment**:
- Staging Database: `docs/acceptance/staging_acceptance.db` (clean SQLite instance populated via Alembic migrations).
- Isolated Backup Directory: `docs/acceptance/backups/`.
- Isolated Scenario Evidence: `docs/acceptance/evidence/AC-XXX/`.

---

## 2. Environment Variables & Safety Configuration

The staging acceptance environment operates with the following non-sensitive configurations:

| Parameter | Staging Value | Purpose / Invariant |
|---|---|---|
| `APP_NAME` | `CodeGuard AI` | Standard application identifier |
| `APP_ENV` | `staging` | Staging execution profile |
| `LOG_LEVEL` | `INFO` | Structured JSON log generation |
| `DATABASE_URL` | `sqlite:///docs/acceptance/staging_acceptance.db` | Dedicated staging database isolation |
| `CELERY_TASK_ALWAYS_EAGER` | `true` | Synchronous task execution for deterministic testing |
| `DEV_AUTH_BYPASS` | `false` | Real JWT and RBAC enforcement during security tests |
| `SECRET_KEY` | `acceptance-test-secret-key-32-chars-long` | Cryptographic key for JWT and HMAC testing |
| `GITHUB_WEBHOOK_SECRET` | `acceptance-webhook-secret-token` | Constant-time HMAC-SHA256 signature verification |
| `LLM_PROVIDER` | `mock` / `gemini` | `mock` when `GEMINI_API_KEY` is not provided |
| `SANDBOX_ALLOWLIST_COMMANDS`| `["pytest", "python -m pytest", "npm test", "npm run test", "ruff check", "eslint"]` | Execution sandbox command allowlist |
| `STATIC_ANALYZERS_ENABLED` | `["ruff", "eslint"]` | Static analysis orchestrator |

---

## 3. Dependency Availability Matrix

| External Service | Host / Port / URL | Status in Test Host | Fallback / Handling Mechanism |
|---|---|---|---|
| **FastAPI Backend** | `http://localhost:8000` | Instantiable via TestClient / Uvicorn | Direct `TestClient` / async execution |
| **Next.js Frontend** | `http://localhost:3000` | Instantiable via Next.js CLI | `tsc --noEmit` build verification |
| **PostgreSQL** | `localhost:5432` | Daemon not running | Native SQLite engine (Alembic verified) |
| **Redis Broker** | `localhost:6379` | Daemon not running | Celery eager execution & in-memory cache |
| **Google Gemini API** | `https://generativelanguage.googleapis.com` | No API key in environment | Deterministic Mock provider; live calls `NOT TESTED` |
| **GitHub REST / GraphQL**| `https://api.github.com` | No App ID / private key in environment | Webhook HMAC verified; live publishing `NOT TESTED` |
| **Execution Sandbox**| Container / Subprocess | Native OS process isolation | Subprocess with command allowlist & timeout containment |

---

## 4. Zero-Secret Policy

No real private keys, GitHub tokens, Gemini API keys, or database credentials may ever be committed, logged, or recorded in acceptance evidence. All test fixtures utilize synthetic strings explicitly designated as test-only (e.g. `sk_live_MOCK_TEST_SECRET_KEY_NEVER_USE_REDACTED`).
