# CodeGuard AI — Golden Regression Reference Baseline

**Document Status**: Active / Authoritative  
**Date**: September 17, 2026  
**Auditor**: Testing & Release Management Team

---

## 1. Reference Scorecard Overview

This document serves as the immutable reference baseline for all future continuous engineering, refactoring, and dependency upgrades. Any future build or merge request must meet or exceed these metrics.

| Evaluation Category | Target Standard | Measured Value | Variance Allowed | Status |
| :--- | :--- | :--- | :--- | :--- |
| **API Pytest Suite** | 100% Pass | 163 / 163 Passed (0 Failures) | 0 Failures | **PASS** |
| **MCP Pytest Suite** | 100% Pass | 9 / 9 Passed (0 Failures) | 0 Failures | **PASS** |
| **Benchmark Precision** | >= 95.0% | 100.0% | -0.0% | **PASS** |
| **Benchmark Recall** | >= 95.0% | 100.0% | -0.0% | **PASS** |
| **Benchmark F1 Score** | >= 0.950 | 1.0000 | -0.0000 | **PASS** |
| **Out-of-Diff Hallucinations**| 0 | 0 Detected | 0 | **PASS** |
| **Acceptance Scenarios** | 30 / 30 | 30 / 30 Passed | 0 Failures | **PASS** |
| **Specialized Audits** | 6 / 6 | 6 / 6 Passed | 0 Failures | **PASS** |
| **Phase 12 Release Gate** | 22 / 22 | 22 / 22 Passed | 0 Failures | **PASS** |
| **Frontend Production Build** | Clean Build | 11 Static/Dynamic Routes | 0 Build Errors | **PASS** |
| **Static Analysis (Ruff)** | 0 Violations | 0 Errors, 0 Warnings | 0 Errors | **PASS** |
| **Static Analysis (Pyright)**| 0 Violations | 0 Errors, 0 Warnings | 0 Errors | **PASS** |
| **Secrets in Repository** | 0 Secrets | 0 Discovered (205 Files Scanned)| 0 Secrets | **PASS** |

---

## 2. Benchmark Ground-Truth Regression Targets (`v1`)

```json
{
  "dataset_version": "v1",
  "scenarios_total": 12,
  "scenarios_passed": 12,
  "scenarios_failed": 0,
  "true_positives": 11,
  "false_positives": 0,
  "false_negatives": 0,
  "precision": 1.0,
  "recall": 1.0,
  "f1": 1.0,
  "duplicate_count": 0,
  "valid_line_rate": 1.0,
  "wrong_file_count": 0,
  "wrong_line_count": 0,
  "exact_severity_rate": 1.0,
  "category_accuracy_rate": 1.0,
  "avg_latency_ms": 121.45,
  "total_tokens": 36000,
  "estimated_cost_usd": 0.09
}
```

---

## 3. Acceptance Criteria Regression Gates (AC-001 to AC-030)

| Scenario ID | Category | Critical Assertion |
| :--- | :--- | :--- |
| **AC-001** | Normal PR | Produces 0 findings on clean PR |
| **AC-002** | Security Vulnerability | Flags SQL injection / CRITICAL finding on line 34 |
| **AC-003** | Error Handling Bug | Flags unhandled exception / BUG on line 40 |
| **AC-004** | Edge Case | Flags ZeroDivisionError on line 55 |
| **AC-005** | Contract Break | Flags missing return type / contract break on line 53 |
| **AC-006** | Performance Defect | Flags N+1 database query defect on line 26 |
| **AC-007** | No-Issue PR | Confirms zero false positive rate |
| **AC-008** | False Positive Trap | Adversarial Judge rejects non-grounded candidate finding |
| **AC-009** | Multi-File Diff | Indexes multi-file changes with strict file boundary separation |
| **AC-010** | Dependency Update | Parses pyproject/package.json without hallucinating vulnerabilities |
| **AC-011** | Large Diff Handling | Processes 1500+ line diff within memory and latency budget |
| **AC-012** | Prompt Injection (Source)| Neutralizes instruction override embedded in source code |
| **AC-013** | Prompt Injection (Comment)| Neutralizes instruction override embedded in code comments |
| **AC-014** | Malicious-Looking String | Safely parses strings containing SQL keywords and exploit signatures |
| **AC-015** | Stale Context | Aborts review when head SHA diverges during analysis |
| **AC-016** | Stale Approval | Invalidates approval when PR author pushes new commits |
| **AC-017** | Duplicate Webhook | Drops duplicate delivery IDs via replay prevention cache |
| **AC-018** | Duplicate Review Request| Skips re-running completed reviews for identical commit SHAs |
| **AC-019** | Concurrent Review Jobs | State machine lock prevents race conditions on running jobs |
| **AC-020** | Gemini Outage Recovery | Recovers gracefully via exponential backoff |
| **AC-021** | Rate-Limited API (429) | Calculates correct sleep duration based on Retry-After headers |
| **AC-022** | MCP Unauthorized Tool | Blocks execution of `execute_shell` via Sentinel policy |
| **AC-023** | MCP Approval Operation | Routes consequential operations (`submit_review`) to approval queue |
| **AC-024** | Approval Expiry | Rejects approvals exceeding 24-hour TTL window |
| **AC-025** | Post-Approval Commit Drift| Rejects publication when current PR head diverges from approval head |
| **AC-026** | Authorized Publication | Transitions approved findings to PUBLISHED with audit log record |
| **AC-027** | GitHub 502 Bad Gateway | Classifies 502 as retryable; classifies 404 as non-retryable |
| **AC-028** | Publication Idempotency| Deterministic composite key prevents duplicate GitHub comments |
| **AC-029** | Worker Crash Recovery | Worker process kill records FAILED state and clean diagnostic message |
| **AC-030** | Infrastructure Degradation| Health probes return degraded status gracefully when Redis is offline |
