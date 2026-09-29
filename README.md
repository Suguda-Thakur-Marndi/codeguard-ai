# CodeGuard AI — Agentic GitHub Pull Request Review Platform

> **Version**: `1.0.0` | **Status**: Verified in Staging & Local Runtimes (Limited Continuation)  
> *Deterministic Tree-sitter AST code intelligence, multi-agent LangGraph review engine, 5-gate adversarial verification judge, MCP zero-trust governance, human authorization gates, and atomic GitHub publication.*

CodeGuard AI is an automated, adversarial-resistant GitHub Pull Request code review platform designed to detect security vulnerabilities, logic bugs, contract shifts, and performance bottlenecks with mathematical line precision and zero hallucinations.

---

## 1. Problem Statement & Solution

Traditional automated code review tools suffer from three fundamental problems:
1. **High False-Positive Noise**: Static analyzers emit cosmetic nitpicks and fail to detect whether an existing caller or decorator already mitigates the issue.
2. **LLM Hallucinations**: Standard AI review bots hallucinate non-existent line numbers, critique unchanged code outside the diff, or recommend unviable code snippets.
3. **Prompt Injection & Autonomous Tool Escapes**: Malicious pull requests containing adversarial comments or indirect prompt injections can compromise reviewer bots that lack zero-trust boundaries.

**CodeGuard AI solves these challenges by combining:**
- **Deterministic AST Context Extraction**: Uses Tree-sitter parsers to bound reviews strictly to modified hunks and enclosing functions.
- **5-Gate Adversarial Judge**: A dedicated verification funnel that checks diff boundaries, caller factuality, actionability, severity calibration, and execution sandbox syntax.
- **Zero-Trust MCP Sentinel**: Hardcoded tool blocklists (`execute_shell`, `eval_code`, etc.) and mandatory human operator approval for consequential actions.
- **Commit Drift Protection**: Approvals are cryptographically bound to the PR head commit SHA; pushing new commits automatically invalidates stale approvals.

---

## 2. Implemented vs. Planned / Pilot-Pending Capabilities

To maintain strict scientific and engineering honesty, CodeGuard AI clearly distinguishes between what is implemented and verified versus what is pending:

| System Dimension | Capability | Status | Evidence / Verification |
| :--- | :--- | :---: | :--- |
| **Code Intelligence** | Tree-sitter AST parsing for Python, TypeScript, JavaScript | **IMPLEMENTED** | `test_tree_sitter_parsers.py` |
| **Code Intelligence** | Language grammars for Go, Rust, Java | **PLANNED** | Scheduled for future milestones |
| **Multi-Agent Review**| LangGraph StateGraph with Comprehension, Bug, Security, Perf, Test, Contract | **IMPLEMENTED** | `test_orchestrator.py`, `test_agents.py` |
| **Adversarial Judge** | 5-Gate filter (Diff boundary, Factuality, Actionability, Severity, Sandbox) | **IMPLEMENTED** | `test_judge.py`, AC-008 |
| **Zero-Trust MCP** | Standalone MCP Sentinel server with forbidden action blocklists & audit logging | **IMPLEMENTED** | `apps/mcp-server/tests/`, AC-022 |
| **Governance & Auth** | Cryptographic human approval gate with commit-drift invalidation (`COMMIT_DRIFT`) | **IMPLEMENTED** | `test_approvals.py`, AC-016 |
| **GitHub Publishing** | Idempotent multi-line PR review comments with automatic secret scrubbing | **IMPLEMENTED** | `test_github_publisher.py`, AC-028 |
| **Acceptance Suite** | 30 end-to-end PR review scenarios + 6 specialized system audits | **IMPLEMENTED** | `scripts/run_acceptance_suite.py` (36/36 PASS) |
| **Operational SRE** | 27 operational release gates (Clean build, Pydantic, Alembic 001-006, Redis fallback)| **IMPLEMENTED** | `verify_phase16.py` (27/27 PASS) |
| **Unit Test Coverage** | 244 automated unit and integration tests | **IMPLEMENTED** | Pytest (244/244 PASS) |
| **Customer Pilot** | Production deployment across external customer repositories | **PILOT PENDING** | Held in `docs/post-pilot/RELEASE_DECISION.md` |
| **Cloud Autoscaling** | Remote Kubernetes / ECS cluster orchestration under live burst traffic | **PILOT PENDING** | Local tests validated; cloud cluster pending |

---

## 3. High-Level System Architecture

```
                    GitHub Pull Request Webhook Event
                                   │
                                   ▼ HMAC-SHA256
                           +───────────────+
                           |  FastAPI API  | <---> [ PostgreSQL 16 ]
                           |  (Port 8000)  |       (27 Relational Tables)
                           +───────┬───────+
                                   │
                         Enqueues  │
                                   ▼
                           +───────────────+
                           |    Redis 7    |
                           |  Task Queue   |
                           +───────┬───────+
                                   │
                        Pulls Task │
                                   ▼
                           +───────────────+
                           | Celery Worker |
                           +───────┬───────+
                                   │
        ┌──────────────────────────┴──────────────────────────┐
        ▼                                                     ▼
┌─────────────────────────────┐             ┌──────────────────────────────────┐
│  packages/code-intelligence │             │    apps/api/app/agents/          │
│  - Tree-sitter AST Parsers  │             │    - LangGraph StateGraph        │
│  - Unified Diff Indexer     │ ──────────> │    - 6 Domain Specialists        │
│  - Context Token Ranker     │             │    - 5-Gate Adversarial Judge    │
└─────────────────────────────┘             └─────────────────┬────────────────┘
                                                              │
                                       Calls Tools over MCP   │
                                                              ▼
                                            ┌──────────────────────────────────┐
                                            │      apps/mcp-server/ (:8001)    │
                                            │      - Zero-Trust Sentinel       │
                                            │      - Forbidden Tools Blocklist │
                                            │      - Append-Only Audit Log     │
                                            └─────────────────┬────────────────┘
                                                              │
                                     Consequential Tools Gate │
                                                              ▼
                                            ┌──────────────────────────────────┐
                                            │      apps/web/ (:3000)           │
                                            │      - Next.js 15 SSR Dashboard  │
                                            │      - Human Approval Gate       │
                                            └─────────────────┬────────────────┘
                                                              │
                                            Publishes Review  │ (If Head SHA Valid)
                                                              ▼
                                            ┌──────────────────────────────────┐
                                            │   GitHub Pull Request Review     │
                                            │   (Idempotent Inline Comments)   │
                                            └──────────────────────────────────┘
```

---

## 4. Technologies Actually Used

- **Backend REST API**: Python 3.11+, FastAPI 0.111, Pydantic v2, Uvicorn.
- **Asynchronous Task Queue**: Celery 5.4, Redis 7.
- **Relational Database**: PostgreSQL 16, SQLAlchemy 2.0 (ORM), Alembic (Migrations).
- **Code Intelligence**: Tree-sitter 0.24 (Python, JavaScript, TypeScript grammars), `unidiff`.
- **AI Agent Orchestration**: LangGraph 0.2, Google GenAI SDK (`gemini-2.5-flash`, `gemini-2.5-pro`).
- **Security Gateway**: Model Context Protocol (MCP) Sentinel tool server, `pyjwt[crypto]`, `cryptography`.
- **Frontend Dashboard**: Next.js 15 (App Router), React 19, Tailwind CSS, Lucide Icons.
- **Testing & Quality**: Pytest 8.2, Ruff 0.4.5 (Linter/Formatter), Pyright (Static Type Checker).

---

## 5. Quick Start (Local Setup)

### Prerequisites:
- Python 3.11+ (Python 3.12 or 3.13 recommended)
- Node.js 20+ (Node.js 22 LTS recommended)
- Git

### Installation Commands:
```bash
# 1. Clone repository
git clone https://github.com/Suguda-Thakur-Marndi/codeguard-ai.git
cd codeguard-ai

# 2. Set up Python virtual environment
python -m venv .venv
# On Windows: .\.venv\Scripts\Activate.ps1
# On Linux/macOS: source .venv/bin/activate

# 3. Install Python monorepo packages in editable mode
pip install -e "./packages/code-intelligence" -e "./apps/api[dev]" -e "./apps/mcp-server"

# 4. Install Next.js frontend dependencies
cd apps/web && npm install && cd ../..

# 5. Configure local environment variables
cp .env.example .env

# 6. Apply database migrations to head (SQLite by default for local dev)
alembic -c apps/api/alembic.ini upgrade head
```

For complete environment variable documentation and service startup commands, see [`docs/SETUP.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/SETUP.md).

---

## 6. Running the Application Locally

Open separate terminal windows with your virtual environment active:

1. **Backend API (`:8000`)**:
   ```bash
   uvicorn app.main:app --app-dir apps/api --port 8000 --reload
   ```
   *Health probe: `curl http://localhost:8000/api/v1/live`*
2. **MCP Sentinel Server (`:8001`)**:
   ```bash
   python -m uvicorn app.server.main:app --app-dir apps/mcp-server --port 8001 --reload
   ```
   *Health probe: `curl http://localhost:8001/health`*
3. **Celery Worker (Asynchronous mode)**:
   ```bash
   celery -A app.workers.celery_app worker --pool=solo -l info
   ```
4. **Next.js Frontend Dashboard (`:3000`)**:
   ```bash
   cd apps/web && npm run dev
   ```

---

## 7. Running the Automated Test Suites

CodeGuard AI includes 244 automated unit tests, 27 operational release gates, and 36 master acceptance scenarios:

```bash
# 1. Run all Unit & Integration tests (244 tests)
pytest apps/api/tests apps/mcp-server/tests -q

# 2. Run Ruff code style & syntax linter
ruff check .

# 3. Run Master SRE Operational Verification Suite (27 gates)
python verify_phase16.py

# 4. Run Master Acceptance Suite (36 scenarios)
python scripts/run_acceptance_suite.py

# 5. Run Empirical Benchmark Suite (12 scenarios)
python benchmark.py run --dataset v1
```

For the comprehensive testing guide, see [`docs/TESTING.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/TESTING.md).

---

## 8. Documentation Index

All technical documentation is organized by domain under `docs/`:

- **Developer Setup**: [`docs/SETUP.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/SETUP.md)
- **Architecture Overview**: [`docs/architecture/SYSTEM_OVERVIEW.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/architecture/SYSTEM_OVERVIEW.md)
- **Relational Data Model (27 Tables)**: [`docs/architecture/DATA_MODEL.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/architecture/DATA_MODEL.md)
- **Agent Orchestration & MCP Flow**: [`docs/architecture/AGENT_AND_MCP_FLOW.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/architecture/AGENT_AND_MCP_FLOW.md)
- **REST API & Integrations**: [`docs/API_AND_INTEGRATIONS.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/API_AND_INTEGRATIONS.md)
- **Production Operations Runbook**: [`docs/operations/RUNBOOK.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/operations/RUNBOOK.md)
- **Maintenance Ownership Matrix**: [`docs/operations/OWNERSHIP.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/operations/OWNERSHIP.md)
- **Testing Pyramid & Verification**: [`docs/TESTING.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/TESTING.md)
- **Maintainer Onboarding Checklist**: [`docs/MAINTAINER_ONBOARDING.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/MAINTAINER_ONBOARDING.md)
- **Phase 19 Post-Pilot Evaluation**: [`docs/post-pilot/FINAL_REPORT.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/post-pilot/FINAL_REPORT.md)
- **Technical Handover Certification**: [`docs/HANDOVER_REPORT.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/HANDOVER_REPORT.md)

---

## 9. Current Operational Status & License

- **Operational Status**: `ACCEPTED (STAGING & LOCAL RUNTIME)`
- **Deployment Status**: `LIMITED CONTINUATION (PENDING AUTHORIZED CUSTOMER PILOT)`
- **License**: Proprietary / Enterprise Evaluation License
