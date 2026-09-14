# CodeGuard AI — Agentic GitHub Pull Request Review Platform

> **Production Release — Phase 8 Verified**  
> *Deterministic AST code intelligence, multi-agent LangGraph review engine, adversarial verification judge, MCP zero-trust governance, human authorization gates, and atomic GitHub publication.*

CodeGuard AI is an enterprise-grade agentic platform that automates GitHub Pull Request security, correctness, and contract reviews with mathematical precision and zero hallucinations.

---

## Production System Architecture

```
                    GitHub
                       │
                       ▼
                GitHub Webhook (HMAC-SHA256)
                       │
                       ▼
                 FastAPI Backend
                       │
          ┌────────────┼─────────────┐
          ▼            ▼             ▼
      PostgreSQL     Redis       MCP Server
          │            │
          └────── Worker Queue ────┐
                       │           │
                       ▼           │
                Review Pipeline    │
                       │           │
                       ▼           │
               Code Intelligence   │
              (Tree-sitter & AST)  │
                       │           │
                       ▼           │
                  LangGraph        │
                       │           │
          ┌────────────┼───────────┴─┐
          ▼            ▼             ▼
      Security     Bug/Error   Test/Contract
        Agent        Agent         Agent
          \            │            /
           \           │           /
            └──────────┼──────────┘
                       │
                       ▼
                Adversarial Judge
                (4-Gate Verification)
                       │
                       ▼
              Execution Validation
                (Docker Sandbox)
                       │
                       ▼
               Governance Policy
                       │
                ┌──────┴──────┐
                ▼             ▼
          Human Approval   Read-only
                │
                ▼
          GitHub Review (Atomic Inline Comments)
                │
                ▼
            Audit Log (Immutable Append-Only)
```

---

## Key Subsystems

### 1. Code Intelligence Engine (`packages/code-intelligence`)
- **Tree-sitter AST Parsing**: Python, JavaScript, and TypeScript language adapters.
- **Unified Diff Parser**: Deterministic hunk parsing with line classification (`LEFT` base vs `RIGHT` head).
- **Enclosing Entity Resolution**: Maps added/modified lines to enclosing function, method, or class AST chunks.
- **Repository Dependency Graph**: Cross-file caller-callee and inheritance graphs stored in PostgreSQL.
- **Context Ranking**: Deterministic token-budgeted context ranking (1.00 for target AST, 0.95 for sibling symbols, 0.85 for direct callers).

### 2. Agentic Multi-Agent Review Pipeline (`apps/api/app/agents`)
- **LangGraph StateGraph**: Orchestrates comprehension, risk-based routing, parallel specialist dispatch, and aggregation.
- **Specialist Agents**:
  - `SecurityAgent`: OWASP Top 10, auth bypass, injection, hardcoded secrets.
  - `BugAgent`: Null dereference, unhandled exceptions, logic drift, off-by-one errors.
  - `TestAgent`: Test contract compliance, regression risk, missing edge-case test coverage.
  - `PerformanceAgent`: Algorithmic complexity, N+1 database queries, resource leaks.
- **Strict Structured Outputs**: JSON schema-validated Pydantic models with token and cost tracking.

### 3. Adversarial Verification & Execution Sandbox (`apps/api/app/agents/judge`, `validation`)
- **4-Gate Adversarial Judge**:
  - *Gate 1*: Diff Boundary Conformity (rejects line hallucinations outside diff hunks).
  - *Gate 2*: Contextual Factuality (detects existing guards/callers mitigating the issue).
  - *Gate 3*: Actionability Heuristics (rejects vague suggestions without concrete resolutions).
  - *Gate 4*: Severity Penalty Audit (downgrades over-inflated severity ratings).
- **Root-Cause Deduplication**: Merges multi-agent duplicate findings into canonical findings.
- **Execution Sandbox**: Isolated ephemeral container execution (`network_mode="none"`, non-root user, CPU/memory limits, 30s timeout, command allowlist).

### 4. Zero-Trust MCP Governance & Human Authorization (`apps/mcp-server`, `apps/api/app/mcp`)
- **Model Context Protocol (MCP)** gateway exposing strictly typed tool definitions.
- **Anti-Self-Approval Enforcement**: AI agents are strictly prohibited from approving their own reviews.
- **Role-Based Authorization**: Only users with `REVIEWER` or `ADMIN` roles can authorize consequential publications.
- **SHA-Bound Approvals & Commit Drift Protection**: Approvals are cryptographically bound to the PR head commit SHA. If a developer pushes new commits, existing approvals are automatically marked `STALE` and rejected.

### 5. Atomic GitHub Publication (`apps/api/app/github`)
- Idempotent review publication with inline comment coordinates strictly validated against diff hunks.
- Automatic secret scrubbers redact bearer tokens, private keys, and API credentials from comment bodies.

### 6. Empirical Benchmarking & Regression Detection (`evaluation`)
- 12 real-world multi-language evaluation scenarios across Security, Bugs, and Contract compliance.
- Automated calculation of Precision, Recall, F1 score, Line Accuracy, and Latency percentiles (P50/P95).
- Regression detector flags performance degradations before deployments.

---

## Monorepo Layout

```
codeguard-ai/
├── apps/
│   ├── api/                      # FastAPI REST API, Celery worker, Alembic migrations
│   │   ├── app/
│   │   │   ├── agents/           # LangGraph orchestrator, specialists, judge, sandbox
│   │   │   ├── api/v1/endpoints/ # Protected REST endpoints (reviews, approvals, audit, etc.)
│   │   │   ├── core/             # Configuration, security, logging
│   │   │   ├── db/               # PostgreSQL connection pooling and ORM repositories
│   │   │   ├── github/           # GitHub App client, JWT auth, review publisher
│   │   │   ├── mcp/              # MCP policy engine and risk classification
│   │   │   ├── models/           # SQLAlchemy 2.0 ORM models (27 tables)
│   │   │   ├── schemas/          # Pydantic v2 schemas
│   │   │   ├── services/         # Domain services (approval, publication, review jobs)
│   │   │   └── workers/          # Celery asynchronous task definitions
│   │   ├── alembic/              # Database schema migrations (001 through 006)
│   │   ├── tests/                # 163 unit and integration tests
│   │   └── Dockerfile            # Production hardened non-root container image
│   │
│   ├── mcp-server/               # Standalone Model Context Protocol gateway
│   │   ├── app/                  # MCP server tools, policies, audit logger, service auth
│   │   ├── tests/                # 9 policy and tool execution tests
│   │   └── Dockerfile            # Hardened non-root MCP container image
│   │
│   └── web/                      # Next.js 15 App Router engineering dashboard
│       ├── app/                  # Dashboard, PR list, Review details, Approvals, Policies
│       ├── components/           # UI components
│       ├── lib/                  # Typed API client
│       └── Dockerfile            # Multi-stage standalone Next.js image
│
├── packages/
│   └── code-intelligence/        # Tree-sitter AST & Context Ranking engine
│
├── evaluation/                   # Empirical benchmarking subsystem & datasets
├── fixtures/                     # Test repositories (Python, JavaScript, TypeScript)
├── scripts/                      # Database backup & restore utilities
├── docs/                         # Runbooks & Disaster Recovery guides
│   ├── RUNBOOK.md                # Operations incident response procedures
│   ├── SECURITY_RUNBOOK.md       # Security incident & secret rotation runbook
│   └── DISASTER_RECOVERY.md      # RPO/RTO & recovery verification procedures
│
├── docker-compose.yml            # Local development orchestration
├── docker-compose.prod.yml       # Production container orchestration
├── Makefile                      # Standardized developer & release commands
└── benchmark.py                  # Benchmarking CLI
```

---

## Getting Started

### Prerequisites
- Python 3.11+ (Python 3.12 recommended)
- Node.js 20+ / 22
- Docker & Docker Compose
- PostgreSQL 16 & Redis 7

### Local Installation
```bash
# 1. Clone repository
git clone https://github.com/your-org/codeguard-ai.git
cd codeguard-ai

# 2. Install dependencies
make install

# 3. Configure environment
cp .env.example .env

# 4. Apply database migrations
make migrate

# 5. Run development servers
make dev
```

### Running Test Suites
```bash
# Run all backend and MCP tests
make test

# Run code linter
make lint

# Validate benchmark dataset integrity
make validate-benchmark

# Run all 6 end-to-end verification suites
make verify-all
```

---

## Production Deployment

### 1. Configure Environment
Create `.env` based on `.env.production.example`:
```bash
cp .env.production.example .env.production
# Populate all required production secrets:
# - GITHUB_APP_ID, GITHUB_PRIVATE_KEY, GITHUB_WEBHOOK_SECRET
# - DATABASE_URL, REDIS_URL, REDIS_PASSWORD
# - GEMINI_API_KEY, SECRET_KEY, MCP_SERVICE_TOKEN
```

### 2. Deploy with Docker Compose
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

### 3. Verify Deployment
```bash
# Check process liveness
curl -f http://localhost:8000/api/v1/live

# Check database and Redis readiness
curl -f http://localhost:8000/api/v1/ready

# Check MCP gateway health
curl -f http://localhost:8001/health
```

---

## Operations & Disaster Recovery

- **Operations Runbook**: [docs/RUNBOOK.md](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/RUNBOOK.md)
- **Security Runbook & Secret Rotation**: [docs/SECURITY_RUNBOOK.md](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/SECURITY_RUNBOOK.md)
- **Disaster Recovery**: [docs/DISASTER_RECOVERY.md](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/DISASTER_RECOVERY.md)
- **Automated Backup**: `python scripts/backup_db.py --output-dir /var/backups`
- **Automated Restore**: `python scripts/restore_db.py --backup-file /var/backups/<backup>.gz --confirm-restore`
