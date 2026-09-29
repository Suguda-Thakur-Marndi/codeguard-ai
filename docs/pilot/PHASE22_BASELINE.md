# CodeGuard AI — Phase 22: System Baseline Report

**Document ID**: `DOC-P22-BASELINE-01`  
**Date**: September 29, 2026  
**Software Version**: `1.0.0`  
**Working Branch**: `main`  
**Base Commit**: `085615eb45da36135a7374b614e3705ad9ca2468`  
**Evaluation Lead**: Principal QA & Performance Engineer  
**Baseline Nature**: **AUTOMATED STAGING & SYNTHETIC HARNESS BASELINE**  

---

## 1. Executive Summary

Before initiating any real-world pull request processing, this baseline report captures the empirical performance, quality, security, and operational metrics of **CodeGuard AI** established under automated testing and staging simulation.

In strict adherence to Phase 22 Step 3 rules:
- **No Mixing of Baselines**: Synthetic staging measurements are clearly separated from real-world pilot telemetry.
- **No Fabricated Data**: Any measurement that requires live customer repositories or cloud deployment is marked explicitly as **NOT AVAILABLE**.
- **Every Metric Grounded in Evidence**: Each recorded metric cites its source, collection methodology, sample size, and analytical limitations.

---

## 2. Quantitative System Baseline

| Metric Dimension | Measured Baseline Value | Benchmark Source / Test Suite | Sample Size | Limitations & Context |
| :--- | :---: | :--- | :---: | :--- |
| **Precision** | **100.0%** (1.0000) | `benchmark.py` (Dataset `v1`) | 12 scenarios | Curated synthetic ground-truth scenarios; does not reflect noisy external codebases. |
| **Recall** | **100.0%** (1.0000) | `benchmark.py` (Dataset `v1`) | 12 scenarios | Measured against known seeded defects (SQLi, N+1, unhandled exceptions). |
| **F1 Score** | **1.0000** | `benchmark.py` (Dataset `v1`) | 12 scenarios | Harmonic mean of synthetic precision and recall. |
| **Inline Line Accuracy** | **100.0%** (12/12) | `benchmark.py` line bounds check | 12 scenarios | Citations strictly mapped to valid AST node spans in synthetic diffs. |
| **Live Probe Latency (P50)**| **4.59 ms** | `verify_phase10.py` load probe | 100 requests | Local HTTP loopback on Windows development workstation. |
| **Live Probe Latency (P95)**| **5.33 ms** | `verify_phase10.py` load probe | 100 requests | Local HTTP loopback; excludes network transit latency. |
| **End-to-End Review Latency**| **602.3 ms** | `verify_phase12.py` Gate 22 | 1 complete cycle | Staging mock provider; covers Webhook -> AST -> AI -> Judge -> Approval -> Publication -> Audit. |
| **Simulated PR Latency (P50)**| **127.7 ms** | `run_acceptance_suite.py` AC-001 | 30 PR scenarios | In-memory FastAPI TestClient with eager Celery worker. |
| **Upstream 429 Retry Backoff**| **4.0 s** | `run_acceptance_suite.py` AC-021 | 1 scenario | Exponential backoff algorithm honoring HTTP `Retry-After` headers. |
| **Model Token Cost / Run** | **$0.000225** | `gemini.py` pricing telemetry | Simulated run | Calculated using Gemini 2.5 Flash pricing formula ($0.075/1M input, $0.30/1M output). |
| **Production Cloud Spend** | **NOT AVAILABLE** | Cloud Billing API | 0 hrs | CodeGuard AI has not been deployed to AWS/GCP/Azure clusters. |
| **API Error Rate** | **0.00%** (0 / 253) | `pytest apps/api/tests` | 253 tests | Monorepo unit/integration tests running under mock test harness. |
| **MCP Tool Server Error Rate**| **0.00%** (0 / 9) | `pytest apps/mcp-server/tests` | 9 tests | Standalone MCP Sentinel server tool schemas and policy checks. |
| **Real Customer PR Volume** | **NOT AVAILABLE (0)** | Customer Repositories | 0 PRs | No external repositories authorized or connected. |
| **Real Developer Acceptance**| **NOT AVAILABLE** | Customer Pull Requests | 0 reviews | No external reviews generated or published. |
| **Real False Positive Rate** | **NOT AVAILABLE** | Customer Codebases | 0 codebases | Cannot measure noise ratio without real-world developer feedback. |

---

## 3. Subsystem Baseline Details

### 3.1 Code Intelligence & AST Parsing
- **Engine**: Tree-sitter multi-language grammar parser (`packages/code-intelligence`).
- **Languages Supported**: Python, TypeScript, JavaScript.
- **Diff Indexing**: Deterministic `ChangedLineIndex` accurately isolates modified hunks.
- **Edge Cases Tested**:
  * Multi-file diffs (`AC-009`): 100% boundary isolation across separate file contexts.
  * Dependency modifications (`AC-010`): Clean package manifest parsing without false positives.
  * Large diff handling (`AC-011`): 1,500 changed lines parsed within memory bounds (<50MB RAM).
  * Binary and unsupported files: Gracefully skipped with debug log (zero crashes).

### 3.2 Agentic Review Engine (LangGraph)
- **Workflow Topology**: StateGraph with 6 specialized agent nodes:
  1. `ComprehensionAgent`: Analyzes PR description, changed files, and intent.
  2. `SecuritySpecialist`: Scans for injection, auth bypass, secret leaks, and sanitization issues.
  3. `ErrorHandlerSpecialist`: Identifies unhandled exceptions, resource leaks, and contract violations.
  4. `TestCoverageSpecialist`: Flags missing test fixtures or coverage regressions on public APIs.
  5. `PerformanceSpecialist`: Detects algorithmic complexity issues, N+1 ORM patterns, and memory bloat.
  6. `ReviewCollector`: Consolidates candidate findings into typed Pydantic structures.
- **Execution Invariant**: Agents operate on read-only AST representations. They possess zero tool access to execute shell commands, alter code files, or publish to GitHub.

### 3.3 Adversarial Verification & Judge
- **Architecture**: 5-Gate deterministic filtering pipeline (`AdversarialJudge`):
  * **Gate 1 (Diff Boundary)**: Hard rejection of any finding citing lines outside the PR diff.
  * **Gate 2 (Deduplication)**: Identical or overlapping findings collapsed using semantic hashing.
  * **Gate 3 (Factuality Verification)**: Verifies that cited code text exists verbatim at the target line.
  * **Gate 4 (Actionability Verification)**: Rejects generic commentary lacking concrete remediation code.
  * **Gate 5 (Severity Realism)**: Adjusts inflated severity ratings against established policy thresholds.
- **Baseline Accuracy**: 100% rejection of hallucinated line references (tested in `AC-008` and `verify_phase12.py`).

### 3.4 MCP Sentinel Governance & Tool Security
- **Architecture**: Standalone Model Context Protocol server enforcing zero-trust access control.
- **Tool Allowlist**: Only read-only, non-destructive tools permitted.
- **Blocked Operations**: All 9 high-risk operations permanently blocked:
  1. `execute_shell`
  2. `modify_filesystem`
  3. `access_environment_variables`
  4. `write_git_repository`
  5. `delete_database_records`
  6. `bypass_approval_workflow`
  7. `elevate_principal_role`
  8. `install_system_packages`
  9. `make_arbitrary_network_calls`
- **Baseline Audit**: 100% of unauthorized tool invocations blocked and logged to immutable audit trail (`verify_phase15.py` Gate 10).

### 3.5 Publication Safeguards & Concurrency
- **Commit Drift Protection**: Human approvals bound strictly to exact `target_commit_sha`. Pushing a new commit immediately transitions pending approval to `STALE` (`AC-016`, `AC-025`).
- **Idempotency Guard**: Deterministic composite key (`installation:repo:head_sha:finding_hash`) prevents duplicate review publication on retried webhook events (`AC-018`, `AC-028`).
- **Replay Protection**: Webhook delivery UUIDs cached with TTL to reject duplicate deliveries (`AC-017`).

---

## 4. Operational & Infrastructure Baseline

### 4.1 Workstation & Runtime Environment
- **Operating System**: Windows 11 Enterprise (Build 26100), Shell: PowerShell 5.1 / 7.x.
- **Python Runtime**: Python 3.13.2 64-bit inside `.venv` virtual environment.
- **Node.js Runtime**: Node.js v24.20.0, npm 11.19.0.
- **Docker Engine**: Docker CLI 29.5.3 installed. **Docker Desktop daemon is offline** (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`).

### 4.2 Database & Migrations
- **ORM / Migrations**: SQLAlchemy 2.0.40 + Alembic 1.15.1.
- **Schema Revisions**: 6 sequential migrations (001_initial_phase1_tables through 006_phase7_benchmarking_tables) creating 27 domain tables.
- **Clean-to-HEAD Upgrade**: Executes in 680.7ms (`verify_phase16.py` Gate 04).
- **Point-in-Time Backup & Restore**: Executes in 367.0ms with 100% table and row count integrity (`verify_phase16.py` Gate 05).

---

## 5. Summary of Baseline Limitations

1. **Synthetic Nature of Accuracy Scores**: The 100% F1 benchmark score is derived from 12 curated scenarios in dataset `v1`. Real-world repositories exhibit significantly higher ambiguity, varied coding styles, and idiosyncratic architectures.
2. **Local Workstation Concurrency**: Latency figures reflect single-user local workstation performance without concurrent multi-tenant webhook traffic.
3. **Absence of Real Production Feedback**: True false-positive rate, developer alert fatigue, and comment actionability cannot be verified until an authorized pilot is executed.
