# CodeGuard AI — Phase 23: Consolidated Evidence-Based Findings Register

**Document ID**: `DOC-P23-REGISTER-01`  
**Date**: September 29, 2026  
**Software Version**: `1.0.0`  
**Working Branch**: `main`  
**Base Commit**: `085615eb45da36135a7374b614e3705ad9ca2468`  
**Evaluation Authorities**: Principal Software Engineer, QA Lead, Security Engineer, SRE Lead  

---

## 1. Register Overview & Governance

This register provides a consolidated, evidence-backed inventory of all technical findings, architectural blockers, environment limitations, and verification observations identified across Phase 21, Phase 22, and Phase 23.

In strict accordance with Phase 23 guidelines:
- **No Fabricated Findings**: Every item is grounded in empirical CLI output, test execution, or static analysis.
- **Clear Defect vs. Limitation Separation**: Code-level defects are strictly distinguished from environment constraints and customer-dependent prerequisites.
- **Deterministic Status Lifecycle**: Each item is assigned one of the standard statuses: `VERIFIED`, `REPRODUCED`, `FIXED`, `FIX VERIFIED`, `OPEN`, `DEFERRED`, `BLOCKED`, `NOT TESTED`, or `NOT APPLICABLE`.

---

## 2. Findings Register Summary Table

| Finding ID | Subsystem | Description | Initial Severity | Current Status | Verification Command / Evidence |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **FND-23-01** | Scanner / Phase 10 | Placeholder scanner false positive on harmless string text in `scripts/run_acceptance_suite.py` | MEDIUM | **FIX VERIFIED** | `python verify_phase10.py` (17/17 PASS); `pytest apps/api/tests/test_placeholder_scanner.py` (6/6 PASS) |
| **FND-23-02** | Linter / Phase 12 | Ruff `I001` import formatting error in `apps/api/tests/test_auth_google.py` | LOW | **FIX VERIFIED** | `ruff check apps/api/tests/test_auth_google.py` (0 errors); `ruff check .` (0 errors across monorepo) |
| **FND-23-03** | Operations / Phase 18 | Local Docker Desktop daemon offline on development workstation | MEDIUM | **NOT TESTED (HOST LIMITATION)** | `docker info` -> Daemon offline (`pipe/dockerDesktopLinuxEngine`); `docker compose config` passes syntactically |
| **FND-23-04** | Pilot / Phase 22 | Absence of authorized customer repositories and real-world customer pilot evidence | HIGH | **BLOCKED — PILOT EVIDENCE UNAVAILABLE** | Inspection of `docs/pilot/` confirms 0 customer repositories authorized; `PILOT NOT EXECUTED — NO REAL-WORLD PILOT EVIDENCE` |
| **FND-23-05** | Security / Ops | Production credentials and cloud secrets unprovisioned on development environment | HIGH | **OPEN (OPERATIONAL PREREQUISITE)** | Staging environment defaults active; production `.env` requires live secret injection prior to cloud launch |
| **FND-23-06** | Typing / Phase 19 | IDE static type analysis warnings on negative configuration test inputs | LOW | **FIX VERIFIED** | `npx pyright apps/api/tests/test_config.py verify_phase16.py` -> 0 errors, 0 warnings, 0 informations |

---

## 3. Detailed Finding Records

### Finding FND-23-01: Placeholder Scanner False Positive on Report Strings
- **Source Phase & Artifact**: Phase 10 & Phase 21 (`docs/PHASE21_REMEDIATION_REPORT.md`, `verify_phase10.py`)
- **Affected Component**: `verify_phase10.py` -> `audit_zero_placeholders()`
- **Reproduction Steps**: Run `python verify_phase10.py` with naive substring matching targeting `raise NotImplementedError`.
- **Expected Behavior**: The scanner flags only executable Python AST `Raise` statements where `NotImplementedError` is instantiated or raised as an unhandled stub. It ignores string constants, docstrings, regex patterns, and markdown report text.
- **Actual Observed Behavior**: Naive regex search flagged harmless string literals in `scripts/run_acceptance_suite.py:1071` (`"- Zero unhandled production placeholders (raise NotImplementedError)"`) and line 1326 (`placeholder_pat = re.compile(...)`), failing the Phase 10 and Phase 11 verifiers.
- **Severity & Impact**: MEDIUM. Caused artificial CI failure on clean, fully-implemented production codebase.
- **Root Cause**: Text-based whole-word substring search lacked AST syntax awareness.
- **Remediation**: Implemented AST-based `scan_file_for_placeholders()` using Python's standard `ast` library to inspect actual `ast.Raise` nodes. Added 6 regression tests in `apps/api/tests/test_placeholder_scanner.py`.
- **Acceptance Criteria**: `verify_phase10.py` passes 17/17 scorecard items; `test_placeholder_scanner.py` validates that real stubs are caught while report strings, regexes, and docstrings pass.
- **Current Status**: **FIX VERIFIED** (Verified 17/17 pass in Phase 10, 9/9 in Phase 11, 36/36 in acceptance suite).

---

### Finding FND-23-02: Ruff I001 Import Formatting in Auth Tests
- **Source Phase & Artifact**: Phase 12 & Phase 21 (`docs/PHASE21_REMEDIATION_REPORT.md`, `apps/api/tests/test_auth_google.py`)
- **Affected Component**: `apps/api/tests/test_auth_google.py:79`
- **Reproduction Steps**: Run `.venv\Scripts\ruff.exe check apps/api/tests/test_auth_google.py`.
- **Expected Behavior**: All import statements adhere to PEP 8 / isort grouping standards at the module top level.
- **Actual Observed Behavior**: `import time` and `import jwt` were declared inside the function body of `test_auth_me_with_bearer_jwt`, triggering Ruff rule `I001: Import block is un-sorted or un-formatted`.
- **Severity & Impact**: LOW. Code style lint violation; zero impact on test correctness or execution.
- **Root Cause**: Ad-hoc local imports inside test function.
- **Remediation**: Hoisted `import time` and `import jwt` to module-level imports following standard library and third-party groupings. Removed redundant local imports.
- **Acceptance Criteria**: `ruff check apps/api/tests/test_auth_google.py` and `ruff check .` exit with code 0.
- **Current Status**: **FIX VERIFIED** (Verified 0 errors across entire repository).

---

### Finding FND-23-03: Workstation Docker Engine Offline
- **Source Phase & Artifact**: Phase 18 & Phase 21 (`docs/PHASE21_REMEDIATION_REPORT.md`, Phase 18 Staging)
- **Affected Component**: Windows Workstation Docker Desktop Linux Engine (`//./pipe/dockerDesktopLinuxEngine`)
- **Reproduction Steps**: Run `docker info` or `docker compose up`.
- **Expected Behavior**: Docker daemon is active, accepts CLI commands, and launches containerized services (`api`, `worker`, `mcp-server`, `web`).
- **Actual Observed Behavior**: Command fails with exit code 1: `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`.
- **Severity & Impact**: MEDIUM (Operational Limitation). Prevents live container startup and container healthcheck validation on this local host machine.
- **Root Cause**: Docker Desktop application is not started on the Windows host.
- **Remediation**:
  1. Docker Compose files (`docker-compose.yml`, `docker-compose.prod.yml`) were verified syntactically via `docker compose config --quiet` (exit code 0).
  2. Live container runtime testing is deferred to staging environments where Docker Desktop / Docker Engine is running.
- **Acceptance Criteria**: Start Docker Desktop and run `docker compose up -d` with successful health probe responses from `http://localhost:8000/api/v1/health`.
- **Current Status**: **NOT TESTED (HOST LIMITATION)** (Documented as an environment limitation).

---

### Finding FND-23-04: Lack of Customer Pilot Evidence & Authorization
- **Source Phase & Artifact**: Pilot Governance Framework (`docs/pilot/PHASE22_PILOT_PLAN.md`, `docs/pilot/PHASE22_FINAL_DECISION.md`)
- **Affected Component**: Pilot Evaluation Gate / External Repository Ingestion
- **Reproduction Steps**: Inspect `docs/pilot/` and repository documentation for customer pilot agreements or external PR review telemetry.
- **Expected Behavior**: Real-world evaluation data from 3–5 representative repositories with developer acceptance rates and noise metrics.
- **Actual Observed Behavior**: Zero customer repositories authorized; zero external pull requests evaluated; zero comments published. Under non-negotiable rules, no synthetic data may be substituted.
- **Severity & Impact**: HIGH (Release Gate Blocker). Prevents General Availability (GA) production release certification.
- **Root Cause**: No customer organization has authorized pilot access.
- **Remediation**: Maintain pilot status as `PILOT NOT EXECUTED — NO REAL-WORLD PILOT EVIDENCE`. Establish structured pilot plan (`docs/pilot/PHASE22_PILOT_PLAN.md`) and require formal customer charter prior to external connection.
- **Acceptance Criteria**: Execute 3–4 week authorized pilot across 3–5 repositories (minimum 50 PRs) with >80% developer acceptance rate.
- **Current Status**: **BLOCKED — PILOT EVIDENCE UNAVAILABLE** (Customer-dependent prerequisite).

---

### Finding FND-23-05: Production Secrets Unprovisioned on Development Environment
- **Source Phase & Artifact**: Phase 16 SRE Readiness (`docs/operations/SECRETS.md`, `verify_phase16.py`)
- **Affected Component**: Environment Configuration (`apps/api/.env`, `apps/mcp-server/.env`)
- **Reproduction Steps**: Inspect local `.env` and environment variables.
- **Expected Behavior**: Production environment contains live, rotating secrets for Google Gemini API, GitHub App private key, production PostgreSQL 16 instance, and Redis 7 cluster.
- **Actual Observed Behavior**: Local environment utilizes mock LLM mode (`LLM_PROVIDER=mock`) and local test database connection strings.
- **Severity & Impact**: HIGH (Deployment Prerequisite). Production cloud deployment cannot function without live credentials.
- **Root Cause**: Intentional zero-secret policy for local repository checkout. Secrets must never be stored in Git.
- **Remediation**: Document secret injection procedures in operations runbooks. Inject live secrets via cloud secret manager (AWS Secrets Manager / GCP Secret Manager / Vault) during production provisioning.
- **Acceptance Criteria**: Live secrets injected via environment variables in staging cluster; zero secrets committed to Git (`verify_phase15.py` Gate 17 passes).
- **Current Status**: **OPEN (OPERATIONAL PREREQUISITE)**.

---

### Finding FND-23-06: Static Type Analysis Warnings on Negative Tests
- **Source Phase & Artifact**: Phase 19 Type Audit (`apps/api/tests/test_config.py`, `verify_phase16.py`)
- **Affected Component**: Pydantic Configuration Tests
- **Reproduction Steps**: Run `npx pyright apps/api/tests/test_config.py verify_phase16.py`.
- **Expected Behavior**: Static type checker passes negative test cases without flagging intentional type-mismatch inputs.
- **Actual Observed Behavior**: Static type checker flagged invalid literal assignments intended to test Pydantic validation error handling.
- **Severity & Impact**: LOW. Static analysis noise on intentional negative test cases.
- **Root Cause**: Testing invalid inputs without explicit typing cast.
- **Remediation**: Wrapped invalid test inputs with `cast(Any, ...)` to inform static analyzers of intentional type coercion tests.
- **Acceptance Criteria**: `pyright` reports 0 errors on target test files.
- **Current Status**: **FIX VERIFIED** (Verified 0 errors, 0 warnings, 0 informations via Pyright 1.1.414).
