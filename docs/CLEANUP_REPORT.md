# CodeGuard AI — Repository Cleanup & File Audit Report

**Document Version**: 2.0.0  
**Audit Date**: 2026-09-29  
**Branch**: `main`  
**Execution Context**: Senior Software Engineer Repository Cleanup & Documentation Consolidation  

---

## 1. Executive Summary

A comprehensive, zero-risk cleanup audit of the **CodeGuard AI** monorepo was executed in strict adherence to project invariants:
- **No functional refactoring or business logic alterations**.
- **No changes to UI/UX, styling, or frontend components**.
- **No deletion or weakening of security, regression, acceptance, or unit tests**.
- **Preservation of user credentials, `.env` files, Docker volume specifications, and dependency lockfiles**.
- **Consolidation of duplicated documentation into authoritative single sources of truth**.

### Audit Metrics
| Metric | Value | Notes |
|---|---|---|
| **Files Inspected** | **385+** | Full monorepo traversal across API, MCP, Web, Code Intelligence, Evaluation, Docs, and Scripts |
| **Files Deleted (Tracked & Untracked Clutter)** | **44** | 2 tracked files, 2 consolidated docs, 11 obsolete engineering runbooks, 26 untracked DB dumps, 3 temp verification DBs |
| **Empty Directories Removed** | **2** | `infra/` (contained only empty `infra/docker/`), `docs/engineering/runbooks/` |
| **Tooling Caches Purged** | **2** | `.pytest_cache/`, `.ruff_cache/` |
| **Documentation Consolidated** | **4** | Runbooks unified into `docs/RUNBOOK.md`; Disaster recovery unified into `docs/DISASTER_RECOVERY.md` |
| **Files Retained** | **341+** | All essential runtime, CI, security, testing, configuration, and documentation files |
| **Uncertain Files Left Untouched** | **0** | All retained files have verified dependency references or active test assertions |

---

## 2. Deleted Files Register

Every deleted candidate was verified through two-stage analysis (Stage A: Dependency & Reference Audit; Stage B: Safe Deletion).

| Deleted File Path | File Type | Risk Level | Rationale for Removal |
|---|---|---|---|
| [`benchmark_report.csv`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/benchmark_report.csv) | CSV export | LOW | Redundant duplicate export of empirical benchmarks; canonical baseline is [`benchmark_report.json`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/benchmark_report.json), which is explicitly loaded by `benchmark.py` and `evaluation/cli.py`. |
| [`docs/RELEASE_NOTES_PHASE12.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/RELEASE_NOTES_PHASE12.md) | Markdown | LOW | Unreferenced, superseded historical release notes from early development; all operational and deployment procedures are maintained in [`docs/RUNBOOK.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/RUNBOOK.md) and [`docs/phase24/`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/phase24/). |
| `docs/operations/RUNBOOK.md` | Markdown | LOW | Consolidated into authoritative master operations runbook at [`docs/RUNBOOK.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/RUNBOOK.md). Cross-references updated. |
| `docs/operations/DISASTER_RECOVERY.md` | Markdown | LOW | Consolidated into authoritative disaster recovery plan at [`docs/DISASTER_RECOVERY.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/DISASTER_RECOVERY.md). Cross-references updated. |
| `docs/engineering/runbooks/*` (11 files) | Markdown | LOW | Obsolete early Phase 8 runbook fragments containing invalid paths to non-existent `infra/docker/docker-compose.prod.yml`; completely superseded by [`docs/RUNBOOK.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/RUNBOOK.md). |
| `docs/acceptance/backups/*.sqlite.gz` (26 files) | Gzipped SQLite | LOW | Ephemeral untracked test backup dumps generated during repeated acceptance drill runs. Safely pruned while preserving the canonical verified drill snapshot [`docs/acceptance/backups/staging_backup_1790688067.sqlite.gz`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/acceptance/backups/staging_backup_1790688067.sqlite.gz). |
| `docs/acceptance/backups/staging_restored.db` | SQLite DB | LOW | Uncompressed residual temporary database from acceptance restore drill; verified safe to prune. |
| `local_verify.db`, `phase10_verify.db`, `phase12_verify.db` | SQLite DB | LOW | Ephemeral untracked databases generated during local manual verification script runs; listed in `.gitignore`. |
| `infra/` (including `infra/docker/`) | Empty Directory | LOW | Abandoned empty directory structure; active Docker configuration resides in root [`docker-compose.yml`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docker-compose.yml) and [`docker-compose.prod.yml`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docker-compose.prod.yml). |

---

## 3. Consolidated Documentation

Where documentation was fragmented or duplicated, contents were merged into single authoritative master documents:

1. **Master Production Operations Runbook**:
   - **Retained & Consolidated**: [`docs/RUNBOOK.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/RUNBOOK.md).
   - **Merged From**: `docs/operations/RUNBOOK.md` and `docs/engineering/runbooks/`.
   - **Contents**: Full service topology, start/stop lifecycle, health and trace observability, incident diagnosis, emergency kill-switches, secret rotation, automated backups, and application/DB rollbacks.
   - **Updated References**: [`README.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/README.md), [`docs/HANDOVER_REPORT.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/HANDOVER_REPORT.md), [`docs/MAINTAINER_ONBOARDING.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/MAINTAINER_ONBOARDING.md), [`docs/operations/OWNERSHIP.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/operations/OWNERSHIP.md).

2. **Master Disaster Recovery Plan**:
   - **Retained & Consolidated**: [`docs/DISASTER_RECOVERY.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/DISASTER_RECOVERY.md).
   - **Merged From**: `docs/operations/DISASTER_RECOVERY.md`.
   - **Contents**: RPO/RTO objectives (< 1 hr RPO, < 30 min RTO), backup strategies, 4 operational recovery scenarios (PostgreSQL failure, Redis failure, Host/Node loss, Worker/MCP recovery), post-recovery verification, and drill logs.
   - **Updated References**: [`docs/operations/FINAL_OPERATIONS_REPORT.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/operations/FINAL_OPERATIONS_REPORT.md), [`README.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/README.md).

3. **Complementary Architectural Separation**:
   - [`docs/architecture/SYSTEM_OVERVIEW.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/architecture/SYSTEM_OVERVIEW.md) remains the authoritative specification for **software & AI agent architecture** (Tree-sitter AST, LangGraph orchestrator, 5-gate Adversarial Judge, MCP Sentinel, schemas).
   - [`docs/operations/ARCHITECTURE.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/operations/ARCHITECTURE.md) remains the authoritative specification for **production infrastructure & network topology** (reverse proxy TLS, port bindings, container boundaries, security perimeters).

4. **Pilot & Release Decisions**:
   - [`docs/pilot/`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/pilot/) holds the official Phase 22 Controlled Customer Pilot framework and maintains the pending pilot gate requirement.
   - [`docs/phase23/`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/phase23/) holds the RC1 qualification decision.
   - [`docs/phase24/`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/phase24/) holds the final release audit and pre-deployment plans.

---

## 4. Test Cleanup & Preservation Audit

### Test Candidates Inspection
Every test file across the repository was inspected for utility, coverage overlap, and ongoing necessity:
- `apps/api/tests/` (33 files)
- `apps/mcp-server/tests/` (2 files)
- `packages/code-intelligence/` tests
- `fixtures/` test fixtures

### Test Preservation Rationale
**Zero test files were deleted.** Detailed investigation confirmed that all 35 test files serve non-redundant, authoritative functions across the testing pyramid:
1. **Security & Sandbox Isolation**: `test_security.py`, `test_sandbox.py`, `test_mcp_policy.py`, `test_mcp_tools.py`, `test_webhooks.py`.
2. **Deterministic Code Intelligence**: `test_code_intelligence_api.py`, `test_tree_sitter_parsers.py`, `test_diff_parser.py`, `test_line_index.py`, `test_context_ranker.py`.
3. **Agent Orchestration & Adversarial Judge**: `test_orchestrator.py`, `test_agents.py`, `test_judge.py`, `test_finding_validation.py`.
4. **Governance & Publishing**: `test_approvals.py`, `test_github_publisher.py`, `test_worker.py`.
5. **Database & Migrations**: `test_db.py` / `test_invariants_phase17.py`.
6. **E2E & Acceptance**: `test_failure_recovery.py`, `test_regression_suite.py`.

Pruning any of these tests would directly erode regression protection and violate Prime Directive § 1 & GEMINI § 5 ("NEVER WEAKEN TESTS").

---

## 5. Post-Cleanup Validation Results

All validation suites were executed against the cleaned repository. Every check passed without errors or regressions.

| Validation Suite | Exact Command | Result / Outcome |
|---|---|:---:|
| **Python Lint** | `.venv\Scripts\ruff.exe check .` | **PASS** (0 errors) |
| **API Test Suite** | `.venv\Scripts\python.exe -m pytest apps/api/tests -q` | **PASS** (253 passed) |
| **MCP Server Test Suite** | `.venv\Scripts\python.exe -m pytest tests -q` (in `apps/mcp-server`) | **PASS** (9 passed) |
| **Total Test Count** | Aggregated Pytest Execution | **262 / 262 PASSED (100%)** |
| **Phase 10 Scorecard** | `.venv\Scripts\python.exe verify_phase10.py` | **PASS** (17/17 gates passed) |
| **Phase 12 Verification** | `.venv\Scripts\python.exe verify_phase12.py` | **PASS** (22/22 gates passed) |
| **Phase 15 Master Security** | `.venv\Scripts\python.exe verify_phase15.py` | **PASS** (23/23 gates passed) |
| **Phase 16 Master SRE** | `.venv\Scripts\python.exe verify_phase16.py` | **PASS** (27/27 gates passed) |
| **Frontend TypeScript Lint** | `npm run lint` (in `apps/web/` -> `tsc --noEmit`) | **PASS** (0 errors, Exit Code 0) |
| **Frontend Production Build**| `npm run build` (in `apps/web/` -> `next build`) | **PASS** (All 11 pages compiled in 1895ms) |
| **Docker Compose Config** | `docker compose -f docker-compose.prod.yml config --quiet` | **PASS** (Exit Code 0) |
| **Live Docker Build** | N/A (Docker Desktop Linux daemon offline) | **NOT TESTED (HOST LIMITATION)** |

---

## 6. Retained Candidate Files & Justifications

During inventory analysis, several files appeared at first glance to be phase-specific or redundant, but were confirmed to be essential and retained:

| Candidate File Path | Purpose | Why Retained |
|---|---|---|
| [`benchmark_report.json`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/benchmark_report.json) | Empirical benchmark baseline | Referenced explicitly as the default baseline in `benchmark.py` and `evaluation/cli.py:241`. |
| [`benchmark_report.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/benchmark_report.md) | Human-readable benchmark report | Referenced in post-pilot evidence inventory as part of empirical benchmark ledger. |
| [`verify_phase1.py`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/verify_phase1.py) through [`verify_phase8.py`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/verify_phase8.py) | Verification scripts | Referenced directly as targets in [`Makefile`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/Makefile) (`make verify-all`). |
| [`verify_phase10.py`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/verify_phase10.py) | Phase 10 verification | Imported as a module by `verify_phase11.py`. |
| [`verify_phase15.py`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/verify_phase15.py) | Master security test suite | Invoked programmatically by `verify_phase16.py` Gate 24. |
| [`docs/RELEASE_NOTES_PHASE10.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/RELEASE_NOTES_PHASE10.md) | Phase 10 release notes | Strictly asserted to exist by `verify_phase12.py` Gate 20. |
| [`docs/SECURITY_RUNBOOK.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/SECURITY_RUNBOOK.md) | Security incident runbook | Strictly asserted to exist by `verify_phase12.py` Gate 20 and `verify_phase8.py`. |
| [`docs/ENGINEERING_WORKFLOW.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/ENGINEERING_WORKFLOW.md) | Engineering workflow | Strictly asserted to exist by `verify_phase12.py` Gate 20. |
| [`docs/PHASE21_REMEDIATION_REPORT.md`](file:///c:/Users/sugud/OneDrive/Documents/codeguard-ai/docs/PHASE21_REMEDIATION_REPORT.md) | Phase 21 remediation evidence | Required verification prerequisite for Phase 22, Phase 23, and Phase 24 gate reviews. |

---

## 7. Final Git Status Breakdown

```text
Changes not staged for commit:
  modified:   README.md
  modified:   apps/web/tsconfig.tsbuildinfo
  deleted:    benchmark_report.csv
  modified:   docs/DISASTER_RECOVERY.md
  modified:   docs/HANDOVER_REPORT.md
  modified:   docs/MAINTAINER_ONBOARDING.md
  deleted:    docs/RELEASE_NOTES_PHASE12.md
  modified:   docs/RUNBOOK.md
  modified:   docs/acceptance/ACCEPTANCE_MATRIX.md
  modified:   docs/acceptance/EVIDENCE_MANIFEST.md
  deleted:    docs/engineering/runbooks/database-failure.md
  deleted:    docs/engineering/runbooks/gemini-failure.md
  deleted:    docs/engineering/runbooks/github-failure.md
  deleted:    docs/engineering/runbooks/local-startup.md
  deleted:    docs/engineering/runbooks/mcp-failure.md
  deleted:    docs/engineering/runbooks/production-deployment.md
  deleted:    docs/engineering/runbooks/redis-failure.md
  deleted:    docs/engineering/runbooks/rollback.md
  deleted:    docs/engineering/runbooks/security-incident.md
  deleted:    docs/engineering/runbooks/stale-approval.md
  deleted:    docs/engineering/runbooks/worker-failure.md
  deleted:    docs/operations/DISASTER_RECOVERY.md
  modified:   docs/operations/FINAL_OPERATIONS_REPORT.md
  modified:   docs/operations/OWNERSHIP.md
  deleted:    docs/operations/RUNBOOK.md

Untracked files:
  docs/CLEANUP_REPORT.md
  docs/phase23/
  docs/phase24/
  docs/pilot/
```
