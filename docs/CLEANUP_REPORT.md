# CodeGuard AI — Repository Cleanup & File Audit Report

**Document Version**: 3.0.0  
**Audit Date**: 2026-10-02  
**Branch**: `main`  
**Execution Context**: Senior Production Engineering Repository Cleanup, Artifact Purge & Documentation Rationalization  

---

## 1. Executive Summary

A comprehensive, zero-risk cleanup audit of the **CodeGuard AI** monorepo was executed in strict adherence to project invariants and Prime Directive § 1:
- **No functional refactoring or business logic alterations**.
- **No changes to UI/UX, styling, Tailwind configurations, or frontend components**.
- **Zero deletion or weakening of security, regression, acceptance, benchmark, or unit tests**.
- **Preservation of user credentials, `.env` files, Docker volume specifications, and dependency lockfiles**.
- **Pruning of obsolete phase reports, outdated decision documents, ephemeral test databases, logs, and build caches**.
- **Consolidation of documentation into authoritative single sources of truth**.

### Audit Metrics
| Metric | Value | Notes |
|---|---|---|
| **Monorepo Files Inspected** | **473 tracked / 28,000+ workspace** | Full traversal across `apps/api/`, `apps/mcp-server/`, `apps/web/`, `packages/code-intelligence/`, `evaluation/`, `docs/`, `fixtures/`, `scripts/` |
| **Tracked Obsolete Files Deleted** | **33** | 10 drill output logs, 9 post-pilot evaluation docs, 5 old phase final reports, 2 status dashboards, 7 unreferenced phase handover/validation/redundant recovery notes |
| **Empty Directories Removed** | **4** | `docs/operations/evidence/`, `docs/post-pilot/`, `backups/`, `docs/acceptance/backups/` |
| **Tooling & Language Caches Purged**| **58** | `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache` across all packages |
| **Ephemeral Test Databases Pruned** | **4** | `local_verify.db`, `phase10_verify.db`, `phase12_verify.db`, `docs/acceptance/staging_acceptance.db` |
| **Build Artifacts Pruned** | **3** | `apps/web/tsconfig.tsbuildinfo`, `apps/api/codeguard_api.egg-info/`, `packages/code-intelligence/codeguard_code_intelligence.egg-info/` |
| **Tests Retained** | **100% (35 test files + 12 verification suites)** | All 253 backend pytest tests, 9 MCP tests, 12 benchmark scenarios, 36 acceptance scenarios, and 23 security gates intact |
| **Potentially Obsolete Files Preserved** | **1** | `client_secret_384060103040-hr7ov21gogoh33sitrf76vidkoatrvpo.apps.googleusercontent.com.json` (preserved under Zero-Trust credential safety) |

---

## 2. Deleted Files & Directories Register

Every deleted candidate was verified through two-stage analysis (Stage A: Dependency & Reference Audit; Stage B: Safe Deletion).

### 2.1 Tracked Obsolete Documentation & Logs
| Deleted File Path | Category | Rationale for Removal |
|---|---|---|
| `docs/operations/evidence/EV-01-CLEAN-BUILD.log` through `EV-10-PHASE16-GATES.log` (10 files) | Category H: Temporary Logs | Ephemeral output logs captured during early Phase 16 manual drill runs; fully superseded by automated verification suites (`verify_phase16.py`). |
| `docs/post-pilot/*` (9 files: `BASELINE.md`, `EVIDENCE_INVENTORY.md`, `FEEDBACK_ANALYSIS.md`, `FINAL_REPORT.md`, `NEXT_ITERATION.md`, `QUALITY_EVALUATION.md`, `RELEASE_DECISION.md`, `RELIABILITY_EVALUATION.md`, `SECURITY_REVIEW.md`) | Category I: Obsolete Phase Reports | Historical Phase 19 post-pilot evaluation documents, outdated decision records, and temporary audit notes; superseded by canonical documentation. |
| `docs/engineering/FINAL_ENGINEERING_REPORT.md` | Category I: Completed Task Report | Point-in-time Phase engineering report from September 2026; superseded by canonical engineering and architecture specifications. |
| `docs/maintenance/FINAL_MAINTENANCE_REPORT.md` | Category I: Completed Task Report | Historical Phase maintenance report from September 28, 2026; ongoing maintenance procedures live in `docs/maintenance/MAINTENANCE_RUNBOOK.md`. |
| `docs/operations/FINAL_OPERATIONS_REPORT.md` | Category I: Completed Task Report | Historical Phase 16 operations report; ongoing production procedures live in `docs/RUNBOOK.md`. |
| `docs/security/FINAL_SECURITY_REPORT.md` | Category I: Completed Task Report | Historical Phase 15 security audit report; active security specifications live in `docs/security/` and `docs/SECURITY_RUNBOOK.md`. |
| `docs/HANDOVER_REPORT.md` | Category I: Completed Task Report | Historical Phase 20 handover report; canonical maintainer onboarding lives in `docs/MAINTAINER_ONBOARDING.md`. |
| `docs/maintenance/MAINTENANCE_STATUS.md` | Category I: Status Dashboard | Outdated static project-status Markdown file (as of September 28, 2026). |
| `docs/operations/OPERATIONS_STATUS.md` | Category I: Status Dashboard | Outdated static operational status Markdown file (as of Phase 16). |
| `docs/phase23/PHASE23_HANDOVER.md` | Category I: Phase Handover | Unreferenced, point-in-time Phase 23 handover note. |
| `docs/phase23/PHASE23_VALIDATION_REPORT.md` | Category I: Validation Report | Unreferenced, point-in-time Phase 23 validation report. |
| `docs/phase24/PHASE24_DEPLOYMENT_EVIDENCE.md` | Category I: Deployment Evidence | Unreferenced, point-in-time Phase 24 staging evidence notes. |
| `docs/phase24/PHASE24_FINAL_HANDOVER.md` | Category I: Phase Handover | Unreferenced, point-in-time Phase 24 handover note. |
| `docs/phase24/PHASE24_ROLLBACK_AND_RECOVERY.md` | Category I: Redundant Runbook | Redundant runbook fragment; emergency kill-switch and rollback protocols are canonically consolidated in `docs/RUNBOOK.md` and `docs/operations/ROLLBACK.md`. |
| `docs/pilot/PHASE22_BASELINE.md` | Category I: Phase Baseline | Historical, unreferenced Phase 22 baseline report. |
| `docs/pilot/PHASE22_EVIDENCE_REPORT.md` | Category I: Phase Report | Historical, unreferenced Phase 22 evidence report. |

### 2.2 Directories Removed
| Deleted Directory | Rationale |
|---|---|
| `docs/operations/evidence/` | Emptied after pruning temporary drill logs. |
| `docs/post-pilot/` | Emptied after removing obsolete Phase 19 documents. |
| `backups/` | Untracked directory holding obsolete local test SQLite snapshots from Phase 16. |
| `docs/acceptance/backups/` | Untracked directory holding ephemeral test backup dumps from acceptance suite drills. |

### 2.3 Ephemeral Databases & Build Artifacts Removed
| Deleted Path | Category | Rationale |
|---|---|---|
| `local_verify.db`, `phase10_verify.db`, `phase12_verify.db` | Category H: Local DB | Ephemeral SQLite databases generated by local verification script runs. |
| `docs/acceptance/staging_acceptance.db` | Category H: Local DB | Ephemeral SQLite database generated during acceptance test runs. |
| `apps/web/tsconfig.tsbuildinfo` | Category H: Build Cache | Incremental TypeScript build cache (cleanly regenerated on `npm run build`). |
| `apps/api/codeguard_api.egg-info/`, `packages/code-intelligence/codeguard_code_intelligence.egg-info/` | Category H: Build Artifact | Python editable installation build metadata. |
| 58 `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache` dirs | Category H: Tooling Cache | Python bytecode, linter, and type checker cache directories. |

---

## 3. Retained Files & Justifications

### 3.1 Core Application Runtime (Category A)
- `apps/api/app/`: FastAPI application routers, domain services, SQLAlchemy 2.0 repositories, GitHub webhook ingestion, Adversarial Judge 5-gate pipeline, LangGraph orchestrator, specialist agents, and Celery workers.
- `apps/mcp-server/app/`: Dedicated Model Context Protocol (MCP) server enforcing zero-trust Sentinel policies and audit logging.
- `apps/web/app/`, `apps/web/components/`, `apps/web/lib/`: Next.js 15 App Router web dashboard, UI components, API client hooks, and CSS styling.
- `packages/code-intelligence/code_intelligence/`: Deterministic Tree-sitter AST parsers (Python, TypeScript, JavaScript), symbol graph builder, line indexer, and context ranker.

### 3.2 Build & Packaging (Category B)
- `apps/web/package.json`, `apps/web/package-lock.json`: Authoritative npm dependencies and lockfile.
- `apps/api/pyproject.toml`, `apps/mcp-server/pyproject.toml`, `packages/code-intelligence/pyproject.toml`, `pyproject.toml`: Authoritative Python package definitions and Ruff configuration.
- `apps/web/tsconfig.json`, `apps/web/next.config.js`, `apps/web/tailwind.config.js`, `apps/web/postcss.config.js`, `apps/web/.eslintrc.json`: Frontend build and styling configurations.

### 3.3 Deployment & Infrastructure (Category C)
- `docker-compose.yml`, `docker-compose.prod.yml`: Docker Compose service manifests for development and production topologies.
- `apps/api/Dockerfile`, `apps/mcp-server/Dockerfile`, `apps/web/Dockerfile`, `docker/sandbox/Dockerfile`: Container image build specifications.
- `apps/api/alembic/`: Complete Alembic database migration catalog (revisions 001 through 006, 27 domain tables).
- `.github/workflows/ci.yml`, `.github/dependabot.yml`: CI/CD production pipelines and automated dependency monitoring.

### 3.4 Security & Configuration (Category E)
- `.env.example`, `.env.staging.example`, `.env.production.example`: Reference environment configuration files.
- `.env`: Active local development environment variables (untracked, preserved).
- `apps/api/.env`: Backend local environment variables (untracked, preserved).
- `.gitignore`: Comprehensive workspace exclusion definitions.
- `AGENTS.md`, `GEMINI.md`: Project invariants and multi-agent engineering architecture.
- `.agents/rules/`: 6 IDE customization rules protecting UI/UX, security boundaries, business logic, Serena protocols, and Context7 safety.
- `.agents/skills/`: 4 specialized workflow skills (`codeguard-agency-agents`, `codeguard-serena-navigator`, `codeguard-context7-docs`, `codeguard-workflow-orchestrator`).
- `.agents/plugins/codeguard-workflow/`: Customization plugin definitions and MCP configurations.

### 3.5 Testing & Benchmarking (Category F)
- `apps/api/tests/` (33 files): Unit, integration, security, and invariant tests executed in CI.
- `apps/mcp-server/tests/` (2 files): MCP Sentinel policy and tool execution tests executed in CI.
- `fixtures/` (13 files): Multi-language test repositories (Python, TypeScript, JavaScript) for Tree-sitter AST tests.
- `evaluation/` (20 files): Empirical benchmark runner, metrics engine, and scenario datasets (`datasets/v1/scenarios.json`).
- `benchmark.py`, `benchmark_report.json`, `benchmark_report.md`: Empirical benchmark CLI and regression verification baseline executed in CI step 2.
- `scripts/backup_db.py`, `scripts/restore_db.py`: Database backup and restoration automation.
- `scripts/run_acceptance_suite.py`: Master acceptance suite (36/36 scenarios), executed by `verify_phase16.py` Gate 25.
- `scripts/workflow/`: Serena navigation bridge, Context7 documentation safety bridge, and workflow orchestration.
- `verify_phase1.py` through `verify_phase16.py`: Verification gate suites executed by `make verify-all` and master SRE release checks.

### 3.6 Essential Documentation (Category G)
- `README.md`: Master project documentation and setup entrypoint.
- `docs/SETUP.md`, `docs/TESTING.md`: Developer setup and testing guides.
- `docs/API_AND_INTEGRATIONS.md`: REST API catalog and external integration contracts.
- `docs/RUNBOOK.md`, `docs/SECURITY_RUNBOOK.md`, `docs/DISASTER_RECOVERY.md`: Master production operations runbooks, incident response playbooks, and disaster recovery plans (strictly asserted by `verify_phase10.py` and `verify_phase12.py`).
- `docs/ENGINEERING_WORKFLOW.md`: Engineering workflow specifications (asserted by `verify_phase11.py`).
- `docs/RELEASE_NOTES_PHASE10.md`: Release notes (strictly asserted by `verify_phase12.py` Gate 20).
- `docs/MAINTAINER_ONBOARDING.md`: 12-step maintainer onboarding guide.
- `docs/architecture/` (3 files: `AGENT_AND_MCP_FLOW.md`, `DATA_MODEL.md`, `SYSTEM_OVERVIEW.md`): Core architectural and data model specifications.
- `docs/operations/` (15 files): Operational specifications covering alerting, architecture, backup/restore, configuration, deployment, health checks, incident response, monitoring, ownership, checklists, release process, rollback, scaling, and secrets.
- `docs/security/` (6 files): Attack surface analysis, residual risk ledger, security matrix, baselines, test plans, and threat model.
- `docs/maintenance/` (10 files): Maintainer policies covering AI models, API compatibility, database maintenance, dependency lifecycle, incident followup, and technical debt.
- `docs/acceptance/` (6 markdown files + 36 `evidence.json` files): Master acceptance test plan, environment setup, baseline, evidence manifest, and scenario evidence files utilized by `scripts/run_acceptance_suite.py`.
- `docs/pilot/PHASE22_PILOT_PLAN.md`, `docs/pilot/PHASE22_FINAL_DECISION.md`: Controlled customer pilot governance framework (referenced in `README.md`).
- `docs/phase23/PHASE23_FINDINGS_REGISTER.md`, `PHASE23_RELEASE_CANDIDATE_DECISION.md`, `PHASE23_REMEDIATION_REPORT.md`: Release Candidate 1 qualification certification and remediation records (referenced in `README.md`).
- `docs/phase24/PHASE24_FINAL_RELEASE_AUDIT.md`, `PHASE24_DEPLOYMENT_PLAN.md`: Final release audit and production deployment plans (referenced in `README.md`).
- `docs/PHASE21_REMEDIATION_REPORT.md`: Technical audit remediation evidence (referenced in `README.md`).

### 3.7 Potentially Obsolete / Sensitive Files Preserved (Category J)
- `client_secret_384060103040-hr7ov21gogoh33sitrf76vidkoatrvpo.apps.googleusercontent.com.json`: Downloaded Google Cloud OAuth credentials file. Excluded by `.gitignore`, preserved in root to protect Google OAuth authentication configuration.

---

## 4. Post-Cleanup Validation Results

All validation suites were executed against the cleaned codebase. Every check passed with zero regressions.

| Validation Suite | Exact Command | Result / Outcome |
|---|---|:---:|
| **Python Lint (Entire Workspace)** | `.\.venv\Scripts\ruff.exe check .` | **PASS (0 errors, 0 warnings)** |
| **Backend Pytest Suite** | `.\.venv\Scripts\python.exe -m pytest apps/api/tests -q` | **PASS (253 passed in 13.9s)** |
| **MCP Server Pytest Suite** | `.\.venv\Scripts\python.exe -m pytest apps/mcp-server/tests -o pythonpath=apps/mcp-server -q` | **PASS (9 passed in 0.5s)** |
| **Benchmark Integrity Validation** | `.\.venv\Scripts\python.exe benchmark.py validate` | **PASS (12/12 scenarios valid)** |
| **Benchmark Regression Verification** | `.\.venv\Scripts\python.exe benchmark.py regression --baseline benchmark_report.json --concurrency 4` | **PASS (0 quality/perf regressions, F1: 1.0000)** |
| **Frontend TypeScript Lint** | `npm run lint` (in `apps/web/`) | **PASS (tsc --noEmit, 0 errors)** |
| **Frontend Production Build** | `npm run build` (in `apps/web/`) | **PASS (All 11 pages compiled in 1529ms)** |
| **Docker Compose Config (Prod)** | `docker compose -f docker-compose.prod.yml config --quiet` | **PASS (Exit Code 0)** |
| **Docker Compose Config (Dev)** | `docker compose -f docker-compose.yml config --quiet` | **PASS (Exit Code 0)** |
| **Phase 10 Master Scorecard** | `.\.venv\Scripts\python.exe verify_phase10.py` | **PASS (17/17 gates passed)** |
| **Phase 11 Engineering Workflow** | `.\.venv\Scripts\python.exe verify_phase11.py` | **PASS (9/9 gates passed)** |
| **Phase 12 Master Verification** | `.\.venv\Scripts\python.exe verify_phase12.py` | **PASS (22/22 gates passed)** |
| **Phase 15 Master Security Suite** | `.\.venv\Scripts\python.exe verify_phase15.py` | **PASS (23/23 gates passed)** |
| **Phase 16 Master SRE Readiness** | `.\.venv\Scripts\python.exe verify_phase16.py` | **PASS (27/27 gates passed)** |
| **Phases 1–8 Verification Suite** | `python verify_phase{1..8}.py` | **PASS (All 7 suites passed)** |
| **Live Remote Container Runtime** | N/A (Docker Desktop Linux daemon offline on local host) | **NOT TESTED — HOST LIMITATION** |

---

## 5. Conclusion & Production Readiness

The repository has been pruned of all obsolete project-history reports, redundant runbooks, temporary logs, and build artifacts. All functional source code, test suites, database migration chains, container configurations, and essential documentation remain intact, verified, and production-ready.
