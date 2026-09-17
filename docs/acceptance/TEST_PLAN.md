# CodeGuard AI — Master Acceptance Test Plan

**Document Version**: 1.0.0  
**Phase**: Final Acceptance, Production-Simulation, and Evidence-Certification  
**Target Coverage**: 30 Core Acceptance Scenarios (AC-001 to AC-030) + 6 Specialized Audits

---

## 1. Scope & Objective

The objective of this test plan is to validate CodeGuard AI end-to-end under realistic production-simulation conditions. All assertions are deterministic and evidence-backed.

---

## 2. Core Scenario Catalog (AC-001 to AC-030)

| Scenario ID | Category | Name & Description | Expected Deterministic Outcome |
|---|---|---|---|
| **AC-001** | Core Workflow | Normal PR with clean code changes | Ingested, AST parsed, context assembled, 0 hallucinated findings |
| **AC-002** | Security | Critical Authorization Check Bypass | Flagged by Security Specialist, exact diff line matched, actionable remediation |
| **AC-003** | Reliability | Error Handling / NoneType Dereference | Flagged by Bug Specialist, unhandled None identified before attribute access |
| **AC-004** | Edge Cases | Boundary Condition (Empty Batch / ZeroDivision) | Flagged by Bug Specialist, empty collection guard requirement identified |
| **AC-005** | Contract/Test | Breaking Public API Return Type Contract | Flagged by Test Specialist, return type tuple discrepancy identified |
| **AC-006** | Performance | N+1 Query Loop in Batch Settlement | Flagged by Performance Specialist, bulk lookup recommendation provided |
| **AC-007** | Precision | No-Issue PR (Docstrings & Typings) | Zero false positive findings generated; clean pass |
| **AC-008** | Precision | False Positive Trap (Internal Helper Guarded) | Adversarial Judge rejects finding after verifying caller enforces authorization |
| **AC-009** | Architecture | Multi-File Pull Request | Correct line and file attribution across multiple modified files |
| **AC-010** | Architecture | Dependency Modification (e.g. pyproject.toml) | Dependency change parsed without hallucinating unverified CVEs |
| **AC-011** | Scalability | Large Diff Context Budgeting | Diff chunking enforced, line limit respected, context within limits |
| **AC-012** | Security | Prompt Injection in Source Code | Source treated strictly as untrusted DATA; instruction not executed |
| **AC-013** | Security | Prompt Injection in Code Comments | Embedded approval bypass instructions rejected; defect still reported |
| **AC-014** | Security | Malicious-Looking String/Data Payload | Data evaluated without triggering policy bypass or secret leakage |
| **AC-015** | Integrity | Stale Context Invalidation | Job detects head SHA divergence and invalidates stale context |
| **AC-016** | Governance | Stale Approval Invalidation | Action rejected if commit SHA changes after human approval is granted |
| **AC-017** | Security | Duplicate Webhook Ingestion | Replay protection drops duplicate delivery via constant-time cache |
| **AC-018** | Reliability | Duplicate Review Request | Idempotency guard skips review if review job already completed |
| **AC-019** | Concurrency | Concurrent Review Requests | State machine prevents concurrent conflicts and duplicate jobs |
| **AC-020** | Resilience | Transient Gemini Provider Failure | Transient error retries with bounded exponential backoff; failures classified |
| **AC-021** | Resilience | Rate-Limited External API (429) | Rate limiter backs off gracefully adhering to Retry-After |
| **AC-022** | MCP Governance| Unauthorized / Forbidden MCP Tool | Sentinel policy strictly blocks forbidden tool executions (e.g. `execute_shell`) |
| **AC-023** | MCP Governance| Approval-Required MCP Tool | High-risk tools routed to human approval gate |
| **AC-024** | Governance | Approval Expiration Enforcement | Expired approval token rejected server-side |
| **AC-025** | Governance | Head SHA Drift After Approval | Publication rejected if target branch head SHA advanced |
| **AC-026** | Governance | Successful Human-Approved Publication | Authorized approval transitions finding to PUBLISHED state |
| **AC-027** | Resilience | Publication Retry on Server Error (502) | 502 error treated as retryable without state corruption |
| **AC-028** | Idempotency | Publication Idempotency Verification | Repeated publication requests do not duplicate GitHub reviews/comments |
| **AC-029** | Resilience | Worker Restart / Task Interruption | Job failure captured safely, error logged, no partial corrupt state |
| **AC-030** | Resilience | Database / Redis Outage Handling | Health check reports degraded status (`/ready` 503) without unhandled crash |

---

## 3. Specialized System Audits

1. **AUDIT-DB**: Clean Database Initialization from Zero (Alembic 001 through 006 migrations applied to fresh database, 27 tables verified).
2. **AUDIT-BK**: Database Backup and Restore Drill (Gzip compression, SHA-256 checksum verification, simulated drop and full restoration via `scripts/backup_db.py` & `scripts/restore_db.py`).
3. **AUDIT-SEC**: Zero-Secret Audit (Scanning entire codebase for API keys, private tokens, or hardcoded secrets).
4. **AUDIT-PH**: Zero-Placeholder Audit (Inspecting production paths for unhandled TODO, FIXME, or NotImplementedError).
5. **AUDIT-OBS**: Observability & Telemetry Trace Drill (End-to-end timeline correlation from T0 Webhook to T10 Publication).
6. **AUDIT-BENCH**: Benchmark & Regression Execution (12 real scenarios evaluated, F1 >= 0.90, 0 regressions).
