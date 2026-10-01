# CodeGuard AI — Master Testing & Verification Guide

**Document ID**: `DOC-TEST-GUIDE-01`  
**Application Version**: `1.0.0`  
**Total Automated Tests**: 244 Pytest Tests | 27 SRE Release Gates | 36 Acceptance Scenarios | 23 Security Gates  
**Last Verified Execution**: 2026-09-29  

---

## 1. Testing Philosophy & Test Pyramid

CodeGuard AI enforces a multi-tier testing pyramid to guarantee that no hallucinations, security regressions, or contract shifts can reach production:

```
                  /\
                 /  \     Level 5: Master SRE Gates (27 Gates)
                /────\    Level 4: Acceptance Scenarios (36 Scenarios)
               /──────\   Level 3: Security & Red-Team Audit (23 Gates)
              /────────\  Level 2: Empirical Benchmarks (12 Scenarios)
             /──────────\ Level 1: Unit & Integration Tests (244 Tests)
            /────────────\
```

- **Zero-Weaken Axiom**: Tests are authoritative. If an existing test fails, the implementation must be fixed; assertions must never be suppressed, deleted, or loosened.
- **Mock vs. Live Testing Boundary**: Deterministic mock providers (`LLM_PROVIDER=mock`) and test fixtures are used in CI and local test harnesses to provide instant, reproducible verification without incurring cloud costs or relying on external internet availability.

---

## 2. Test Execution Commands & Verified Outcomes

### 2.1 Level 1: Unit & Integration Test Suites
Executes all unit and integration tests across the API backend.

```bash
# Run all 253 backend API tests
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q
```
- **Target Subsystems**: FastAPI routes, Pydantic schemas, Celery tasks, Tree-sitter parsers, Context ranker, Adversarial Judge, Zero-Trust Policy Engine, and Database repositories.
- **Verified Outcome**: `253 passed in 18.5s` (`100% PASS, 0 FAIL`).

---

### 2.2 Level 2: Empirical Benchmarking & Regression Detection
Validates specialist agent accuracy, line attribution, and latency against curated multi-language ground-truth scenarios.

```bash
# 1. Validate dataset integrity
python benchmark.py validate

# 2. Run 12-scenario benchmark run
python benchmark.py run --dataset v1

# 3. Check for quality or latency regressions against baseline
python benchmark.py regression --baseline benchmark_report.json
```
- **Verified Outcome**: Precision=100.0%, Recall=100.0%, F1=1.0000, Line Accuracy=100.0%, P50=132.7ms, 0 regressions detected.

---

### 2.3 Level 3: Security & Red-Team Audit Suite
Simulates 23 aggressive adversarial attack scenarios including prompt injection, JWT forgery, role escalation, and secret leakage.

```bash
python verify_phase15.py
```
- **Verified Outcome**: `23/23 SECURITY GATES PASSED` (Zero secrets, zero unauthorized tool executions, zero prompt bypasses).

---

### 2.4 Level 4: Master Acceptance & Production-Simulation Suite
Simulates 30 complete end-to-end pull request review lifecycles (AC-001 through AC-030) and 6 specialized system audits (DB, Backup, Observability, Secrets, Placeholders, Benchmarks).

```bash
python scripts/run_acceptance_suite.py
```
- **Verified Outcome**: `36/36 PASSED (30 scenarios + 6 audits)` in 13.68s.

---

### 2.5 Level 5: Master SRE & Operational Verification Suite
Evaluates all 27 operational release gates including Next.js standalone build, Pydantic fail-fast validation, Alembic clean-to-HEAD upgrade, Redis fallback, and Celery crash recovery.

```bash
python verify_phase16.py
```
- **Verified Outcome**: `27/27 GATES PASSED` in 18.8s.

---

## 3. Code Quality, Linting & Type Analysis

### 3.1 Python Linting & Formatting (Ruff)
```bash
# Check code style, import sorting, and syntax rules
.\.venv\Scripts\ruff.exe check .

# Automatically apply safe formatting fixes
.\.venv\Scripts\ruff.exe format .
```
- **Configuration**: Target Python 3.11, line length 100 (`pyproject.toml`).
- **Verified Outcome**: `All checks passed!`.

### 3.2 Static Type Checking (Pyright)
```bash
# Verify static type safety on modified modules
npx --no-install pyright apps/api/tests/test_config.py verify_phase16.py
```
- **Configuration**: `pyrightconfig.json` with `.venv` execution path and monorepo extra paths.
- **Verified Outcome**: `0 errors, 0 warnings, 0 informations`.

### 3.3 Frontend Type Checking & Production Build (Next.js)
```bash
cd apps/web

# Check TypeScript validity
npm run lint

# Compile Next.js 15 standalone production bundle
npm run build
```
- **Verified Outcome**: 11 static and dynamic routes compiled in 1,940ms; 0 TypeScript errors.

---

## 4. Continuous Integration (CI/CD) Workflows

The repository includes automated GitHub Actions workflows in `.github/workflows/`:

1. **`ci.yml`**:
   - Triggers on every push and pull request to `main`.
   - Matrix testing across Python 3.11, 3.12, 3.13.
   - Executes Ruff linting, Pytest test suites, and Next.js standalone build.
   - Enforces zero regression against `benchmark_report.json`.
2. **`dependabot.yml`**:
   - Weekly automated security audits for Python (`pip`) and Node.js (`npm`) packages.

---

## 5. Known Test Limitations & Test Boundaries

1. **Simulated LLM Provider in Automated Tests**:
   - Tests run by default with `LLM_PROVIDER=mock` to ensure determinism and eliminate cloud API billing during test cycles.
   - Testing live Gemini model inference requires setting `LLM_PROVIDER=gemini` and providing an active `GEMINI_API_KEY`.
2. **Host Container Daemon Availability**:
   - Tests executing in local virtual environments validate AST-level execution sandboxes; kernel-level gVisor / seccomp container isolation requires running on a host with an active Linux Docker engine daemon.
3. **Absence of Real-World Customer Repositories**:
   - All acceptance and benchmark scenarios operate on synthetic test fixtures; testing on live customer repositories remains to be conducted during an authorized customer pilot.
