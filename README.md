# CodeGuard AI — Agentic GitHub Pull Request Review Platform

> **Version**: `1.0.0` | **Release Stage**: `Release Candidate 1 (RC1) Qualified` | **Operational Status**: `ACCEPTED (Staging & Local Runtime)`  
> *Deterministic Tree-sitter AST code intelligence, multi-agent LangGraph review engine, 5-gate adversarial verification judge, zero-trust deterministic policy governance, cryptographic human authorization gates, and direct atomic GitHub publication.*

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15%20(App%20Router)-black.svg)](https://nextjs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Tree-sitter](https://img.shields.io/badge/Tree--sitter-0.24-green.svg)](https://tree-sitter.github.io/)
[![Unit & Integration Tests](https://img.shields.io/badge/tests-253%20passed%20(100%25)-brightgreen.svg)](#7-running-the-automated-test-suites)
[![SRE Gates](https://img.shields.io/badge/SRE%20Gates-27%2F27%20passed-brightgreen.svg)](#7-running-the-automated-test-suites)
[![Security Gates](https://img.shields.io/badge/Security%20Gates-23%2F23%20passed-brightgreen.svg)](#7-running-the-automated-test-suites)

CodeGuard AI is an automated, adversarial-resistant GitHub Pull Request code review platform designed to detect security vulnerabilities, logic bugs, contract shifts, and performance bottlenecks with mathematical line precision and zero hallucinations.

---

## 1. Problem Statement & Solution

Traditional automated code review tools suffer from three fundamental problems:
1. **High False-Positive Noise**: Static analyzers emit cosmetic nitpicks and fail to detect whether an existing caller, decorator, or framework pattern already mitigates the issue.
2. **LLM Hallucinations**: Standard AI review bots hallucinate non-existent line numbers, critique unchanged code outside the diff, or recommend unviable code snippets.
3. **Prompt Injection & Autonomous Tool Escapes**: Malicious pull requests containing adversarial comments or indirect prompt injections can compromise reviewer bots that lack zero-trust boundaries.

**CodeGuard AI solves these challenges by combining:**
- **Deterministic AST Context Extraction**: Uses Tree-sitter parsers to bound reviews strictly to modified hunks and enclosing functions, constructing a deterministic `ChangedLineIndex`.
- **5-Gate Adversarial Judge**: A dedicated verification funnel that checks diff boundaries, caller factuality, actionability, severity calibration, and execution sandbox syntax before any finding is admitted.
- **Zero-Trust Policy Engine**: Hardcoded tool blocklists (`execute_shell`, `eval_code`, `delete_repo`, etc.) and mandatory human operator approval for consequential actions.
- **Commit Drift Protection**: Approvals are cryptographically bound to the PR head commit SHA; pushing new commits automatically invalidates stale approvals (`COMMIT_DRIFT`).

---

## 2. Implemented vs. Planned / Pilot-Pending Capabilities

To maintain strict scientific and engineering honesty, CodeGuard AI clearly distinguishes between verified production capabilities and planned milestones:

| System Dimension | Capability | Status | Evidence / Verification |
| :--- | :--- | :---: | :--- |
| **Code Intelligence** | Tree-sitter AST parsing for Python, TypeScript, JavaScript | **IMPLEMENTED** | `test_tree_sitter_parsers.py`, `ChangedLineIndex` |
| **Code Intelligence** | Language grammars for Go, Rust, Java | **PLANNED** | Scheduled for future milestones |
| **Multi-Agent Review**| LangGraph StateGraph with Comprehension, Bug, Security, Perf, Test, Contract specialists | **IMPLEMENTED** | `test_orchestrator.py`, `test_agents.py` |
| **Adversarial Judge** | 5-Gate filter (Diff boundary, Factuality, Actionability, Severity, Sandbox) | **IMPLEMENTED** | `test_judge.py`, AC-008 |
| **Zero-Trust Policy Engine** | In-process policy engine with forbidden action blocklists & audit logging | **IMPLEMENTED** | `apps/api/app/core/policy.py`, AC-022 |
| **Governance & Auth** | Cryptographic human approval gate with commit-drift invalidation (`COMMIT_DRIFT`) | **IMPLEMENTED** | `test_approvals.py`, AC-016 |
| **GitHub Publishing** | Idempotent multi-line PR review comments with automatic secret scrubbing | **IMPLEMENTED** | `test_github_publisher.py`, AC-028 |
| **Unit & Integration**| 253 automated tests across Backend API | **IMPLEMENTED** | `pytest apps/api/tests` (253/253 PASS, 100%) |
| **Master Security** | 23 master security verification gates (Auth, RBAC, tenant isolation, injections) | **IMPLEMENTED** | `verify_phase15.py` (23/23 PASS) |
| **Operational SRE** | 27 operational release gates (Clean build, Pydantic, Alembic 001-006, Redis fallback)| **IMPLEMENTED** | `verify_phase16.py` (27/27 PASS) |
| **Acceptance Suite** | 30 end-to-end PR review scenarios + 6 specialized system audits | **IMPLEMENTED** | `scripts/run_acceptance_suite.py` (36/36 PASS) |
| **RC1 Qualification**| Phase 23 audit remediation (AST bounds, token limits, Celery retry, rate limits) | **IMPLEMENTED** | [`docs/phase23/PHASE23_RELEASE_CANDIDATE_DECISION.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/phase23/PHASE23_RELEASE_CANDIDATE_DECISION.md) |
| **Customer Pilot** | Production deployment across external customer repositories | **PILOT READY** | Pilot plan in [`docs/pilot/`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/pilot/); held pending explicit authorization |
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
                                       Direct Service Call    │
                                                              ▼
                                            ┌──────────────────────────────────┐
                                            │      apps/api/app/core/policy.py │
                                            │      - Zero-Trust Policy Engine  │
                                            │      - Forbidden Actions (9 ops) │
                                            │      - Immutable Audit Logging   │
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
- **Relational Database**: PostgreSQL 16, SQLAlchemy 2.0 (ORM), Alembic (Migrations 001–006).
- **Code Intelligence**: Tree-sitter 0.24 (Python, JavaScript, TypeScript grammars), `unidiff`.
- **AI Agent Orchestration**: LangGraph 0.2, Google GenAI SDK (`gemini-2.5-flash`, `gemini-2.5-pro`).
- **Security Governance**: Zero-Trust Policy Engine (`app.core.policy`), `pyjwt[crypto]`, `cryptography`.
- **Frontend Dashboard**: Next.js 15 (App Router), React 19, Tailwind CSS, Lucide Icons.
- **Testing & Quality**: Pytest 8.2, Ruff 0.4.5 (Linter/Formatter), Pyright / TypeScript Compiler (`tsc`).

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
pip install -e "./packages/code-intelligence" -e "./apps/api[dev]"

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
2. **Celery Worker (Asynchronous mode)**:
   ```bash
   celery -A app.workers.celery_app worker --pool=solo -l info
   ```
3. **Next.js Frontend Dashboard (`:3000`)**:
   ```bash
   cd apps/web && npm run dev
   ```

---

## 7. Running the Automated Test Suites

CodeGuard AI includes 253 automated unit/integration tests, 27 operational release gates, 23 master security gates, and 36 master acceptance scenarios:

```bash
# 1. Run all Backend API Unit & Integration tests (253 tests)
pytest apps/api/tests -q

# 2. Run Ruff code style & syntax linter (0 errors)
ruff check .

# 3. Run Frontend TypeScript type checker (0 errors)
cd apps/web && npm run lint && cd ../..
```

# 5. Run Master SRE Operational Verification Suite (27 gates)
python verify_phase16.py

# 6. Run Master Security Verification Suite (23 gates)
python verify_phase15.py

# 7. Run Core Architecture Scorecard (17 gates)
python verify_phase10.py

# 8. Run Master Acceptance Suite (36 scenarios)
python scripts/run_acceptance_suite.py

# 9. Run Empirical Benchmark Suite (12 scenarios)
python benchmark.py run --dataset v1
```

For the comprehensive testing guide, see [`docs/TESTING.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/TESTING.md).

---

## 8. Documentation Index

Technical documentation is organized by domain across the repository:

### Architecture & System Design
- [`docs/architecture/SYSTEM_OVERVIEW.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/architecture/SYSTEM_OVERVIEW.md) — Multi-agent graph, state transitions, and Tree-sitter pipeline.
- [`docs/architecture/DATA_MODEL.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/architecture/DATA_MODEL.md) — Relational PostgreSQL schema (27 tables, constraints, indexes).
- [`docs/architecture/AGENT_AND_REVIEW_FLOW.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/architecture/AGENT_AND_REVIEW_FLOW.md) — Detailed agent coordination, policy engine, and direct review publication contracts.
- [`docs/operations/ARCHITECTURE.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/operations/ARCHITECTURE.md) — Production operations topology and service dependencies.

### Security, Governance & Risk
- [`docs/security/THREAT_MODEL.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/security/THREAT_MODEL.md) — Zero-trust boundary, prompt injection mitigations, STRIDE threat model.
- [`docs/SECURITY_RUNBOOK.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/SECURITY_RUNBOOK.md) — Operational security incident procedures and token revocation.
- [`docs/security/ATTACK_SURFACE.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/security/ATTACK_SURFACE.md) — Attack surface enumeration and defense mechanisms.
- [`docs/security/SECURITY_ACCEPTANCE_MATRIX.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/security/SECURITY_ACCEPTANCE_MATRIX.md) — Verified security assertions.

### Operations, SRE & Runbooks
- [`docs/RUNBOOK.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/RUNBOOK.md) — Master operations runbook with alert triage, SLIs, and SLOs.
- [`docs/DISASTER_RECOVERY.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/DISASTER_RECOVERY.md) — Database backup restoration, failover, and data loss prevention.
- [`docs/operations/DEPLOYMENT.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/operations/DEPLOYMENT.md) — Containerized deployment procedures and Docker Compose configurations.
- [`docs/operations/OWNERSHIP.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/operations/OWNERSHIP.md) — Service ownership matrix, escalations, and SLA definitions.

### Developer & Maintainer Guides
- [`docs/SETUP.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/SETUP.md) — Comprehensive developer setup and environment variable reference.
- [`docs/API_AND_INTEGRATIONS.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/API_AND_INTEGRATIONS.md) — REST API endpoints, schemas, and GitHub App webhook contracts.
- [`docs/ENGINEERING_WORKFLOW.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/ENGINEERING_WORKFLOW.md) — Multi-agent pairing guidelines, git hygiene, and coding standards.
- [`docs/MAINTAINER_ONBOARDING.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/MAINTAINER_ONBOARDING.md) — New maintainer walkthrough and quick-start verification.
- [`AGENTS.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/AGENTS.md) — Multi-agent engineering architecture, roles, and rules.
- [`GEMINI.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/GEMINI.md) — AI engineering orchestrator invariants and guardrails.

### Release Milestones, Audits & Cleanup
- [`docs/PHASE21_REMEDIATION_REPORT.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/PHASE21_REMEDIATION_REPORT.md) — Phase 21 technical audit findings and systematic remediation.
- [`docs/pilot/PHASE22_PILOT_PLAN.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/pilot/PHASE22_PILOT_PLAN.md) — Controlled pilot framework and real-world evaluation protocol.
- [`docs/pilot/PHASE22_FINAL_DECISION.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/pilot/PHASE22_FINAL_DECISION.md) — Pilot gate governance and evidence standards.
- [`docs/phase23/PHASE23_REMEDIATION_REPORT.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/phase23/PHASE23_REMEDIATION_REPORT.md) — Deep-dive audit resolving 4 critical hardening items (AST bounds, token limits, Celery retry, rate limits).
- [`docs/phase23/PHASE23_RELEASE_CANDIDATE_DECISION.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/phase23/PHASE23_RELEASE_CANDIDATE_DECISION.md) — Release Candidate 1 (RC1) qualification certification.
- [`docs/phase24/PHASE24_FINAL_RELEASE_AUDIT.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/phase24/PHASE24_FINAL_RELEASE_AUDIT.md) — Final release qualification and pre-deployment audit.
- [`docs/phase24/PHASE24_DEPLOYMENT_PLAN.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/phase24/PHASE24_DEPLOYMENT_PLAN.md) — Production deployment runbook, health probes, and rollback procedures.
- [`docs/CLEANUP_REPORT.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/CLEANUP_REPORT.md) — Monorepo cleanup audit, removed artifacts, and post-cleanup test verification.

---

## 9. Current Operational Status & License

- **Operational Status**: `ACCEPTED (STAGING & LOCAL RUNTIME)`
- **Release Qualification**: `RELEASE CANDIDATE 1 (RC1) QUALIFIED`
- **Customer Pilot Status**: `PILOT READY (PENDING AUTHORIZED EXTERNAL REPOSITORIES)`
- **License**: Proprietary / Enterprise Evaluation License
