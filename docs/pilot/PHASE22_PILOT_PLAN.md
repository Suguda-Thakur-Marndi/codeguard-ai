# CodeGuard AI — Phase 22: Controlled Customer Pilot Plan

**Document ID**: `DOC-P22-PLAN-01`  
**Date**: September 29, 2026  
**Software Version**: `1.0.0`  
**Working Branch**: `main`  
**Base Commit**: `085615eb45da36135a7374b614e3705ad9ca2468`  
**Role Authorities**: Principal Software Engineer, QA Lead, Security Engineer, SRE Lead, Pilot Evaluation Lead  
**Pilot Operational Status**: **STOPPED / PRE-FLIGHT ENTRY GATE BLOCKED**  
**Customer Repository Access Status**: **UNAUTHORIZED (0 REPOSITORIES AUTHORIZED)**  

---

## 1. Executive Summary & Purpose

The objective of **Phase 22** is to establish the governance, architectural safeguards, scope boundaries, and execution protocol for a controlled, real-world customer pilot of **CodeGuard AI**, and—**only when explicitly authorized**—to execute and evaluate the platform against real-world pull requests.

In strict adherence to the **Non-Negotiable Rules** of Phase 22 and the repository Prime Directive (`AGENTS.md`, `GEMINI.md`):
1. **Zero External Access Without Explicit Authorization**: CodeGuard AI will **never** connect to customer GitHub organizations, query external repositories, inspect proprietary code, or publish comments without written stakeholder sign-off and explicit user authorization.
2. **Zero Data Fabrication**: All pilot metrics, repository identities, pull request characteristics, developer feedback, and performance latencies must derive from verifiable evidence. If no pilot occurred, it must be reported honestly as `PILOT NOT EXECUTED — NO REAL-WORLD PILOT EVIDENCE`.
3. **Preservation of System Invariants**: No UI/UX redesigns, business logic alterations, security bypasses, or test weakenings are permitted.

---

## 2. Pilot Entry Conditions Verification

Before connecting to any external environment or initiating any pilot activity, the Phase 22 entry conditions were empirically audited against the active codebase and recent remediation records (`docs/PHASE21_REMEDIATION_REPORT.md`):

| Entry Condition | Requirement | Empirical Verification Result | Status |
| :--- | :--- | :--- | :---: |
| **Phase 10 Blocker** | Placeholder scanner false positive resolved | AST-based detection in `verify_phase10.py` verified; 6 regression tests in `test_placeholder_scanner.py` pass; `verify_phase10.py` score: 17/17 PASS. | **VERIFIED** |
| **Phase 11 Blocker** | Multi-agent workflow and probe gates verified | `verify_phase11.py` executed: 9/9 workflow gates pass with 0 regressions. | **VERIFIED** |
| **Phase 12 Blocker** | Ruff linter I001 import formatting resolved | `test_auth_google.py` imports hoisted; `ruff check .` passes with 0 errors across monorepo; `verify_phase12.py` score: 22/22 PASS. | **VERIFIED** |
| **Security Gates** | Zero-trust, HMAC webhook auth, prompt isolation, sandbox allowlist | `verify_phase15.py` executed: 23/23 security gates pass (0 secrets in 206 files, tamper-proof replay cache, MCP Sentinel policies active). | **VERIFIED** |
| **Operational Gates** | Database migrations, backup/restore drills, fail-fast config, health probes | `verify_phase16.py` executed: 27/27 operational gates pass (Alembic clean-to-HEAD 001–006, SQLite backup/restore verified, Redis fallback active). | **VERIFIED** |
| **Master Acceptance** | 30 PR scenarios + 6 system audits pass | `scripts/run_acceptance_suite.py` executed: 36/36 pass (AC-001..AC-030, AUDIT-DB..AUDIT-BENCH). | **VERIFIED** |
| **Frontend Production** | Next.js 15 App Router static generation and type safety | `npm run lint` (`tsc --noEmit`) passes; `npm run build` generates 11/11 pages with 0 errors. | **VERIFIED** |
| **Docker Staging Runtime**| Local container engine and service startup verified | `docker compose -f docker-compose.yml config` and `docker-compose.prod.yml config` pass syntax validation. **However**, host Docker Desktop engine is offline (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`). Live container runtime startup is unverified on this host. | **NOT TESTED (LIMITATION)** |
| **Production Credentials** | Live production API keys and certificates provisioned | `GEMINI_API_KEY`, GitHub App private key, production PostgreSQL 16 connection string, and Redis password are not injected into local `.env` (staging defaults active). | **OPEN (PRE-REQUISITE)** |
| **Customer Authorization** | Written authorization and scope approval from repository owners | **No customer authorization agreement or pilot charter has been provided.** | **BLOCKED (CRITICAL)** |

### Entry Gate Verdict:
> [!CAUTION]
> **PILOT EXECUTION BLOCKED**: Because customer repository authorization has **NOT** been granted, and host Docker runtime validation is offline, **CodeGuard AI MUST NOT connect to external repositories or execute a real-world customer pilot.** The platform must remain strictly in local/staging verification mode.

---

## 3. Pilot Scope & Repository Archetype Design

To prepare for future authorized execution, a representative pilot scope has been designed for **3–5 repositories** across diverse languages and architectures. In accordance with Rule 2 and Rule 7, no customer names are invented; archetypes represent target operational profiles:

| Target Archetype | Identifier (Tokenized) | Primary Stack | Target Size (LOC) | Typical PR Volume | Primary Evaluation Focus | Publication Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Repo Archetype A** | `TARGET-REPO-PY-01` | Python 3.11+, FastAPI, SQLAlchemy | 25,000–50,000 | 15–20 PRs/week | AST context ranking, async error handling, SQL injection, N+1 query detection | Read-Only (Shadow Mode) |
| **Repo Archetype B** | `TARGET-REPO-TS-02` | TypeScript, React 19, Next.js 15 | 30,000–60,000 | 20–25 PRs/week | Server/Client component boundary leaks, prototype pollution, XSS, contract breakage | Read-Only (Shadow Mode) |
| **Repo Archetype C** | `TARGET-REPO-GO-03` | Go 1.22+, gRPC, Protobuf | 15,000–35,000 | 10–15 PRs/week | Concurrency data races, goroutine leaks, error wrapping, nil pointer dereferences | Read-Only (Shadow Mode) |
| **Repo Archetype D** | `TARGET-REPO-POLY-04`| Polyglot Monorepo (Python/TS) | 80,000–150,000 | 30–40 PRs/week | Multi-file diff boundary isolation, cross-module dependency tracking, large diffs (>1,000 lines) | Read-Only (Shadow Mode) |

### Pull Request Category Coverage Matrix:
Every authorized pilot repository must evaluate pull requests across 7 mandatory test categories:
1. **Security Vulnerabilities**: High/Critical severity issues (OWASP Top 10, CWE-89 SQLi, CWE-79 XSS, SSRF).
2. **Error Handling & Correctness**: Unhandled exceptions, bare `except:`, division by zero, unclosed resources.
3. **Test Coverage Gaps**: Public interface modifications lacking corresponding unit/integration test assertions.
4. **Performance Defects**: Algorithmic bottlenecks, N+1 ORM query patterns, redundant loops.
5. **No-Issue Clean PRs**: Well-crafted pull requests containing zero actionable defects (evaluating false positive suppression).
6. **Large Multi-File Diffs**: PRs modifying >10 files or >1,000 changed lines (evaluating chunking, token budgets, and diff-boundary accuracy).
7. **Adversarial / Malicious Injection PRs**: Pull requests containing embedded prompt injection attempts in diffs, commit messages, or PR comments (tested via synthetic fixtures only).

---

## 4. Operational Modes: Read-Only / Shadow Mode Specification

CodeGuard AI supports three operational modes. The pilot must strictly begin at **Level 0 (Read-Only Shadow Mode)**:

```
[Level 0: Read-Only Shadow Mode] ──(Authorized Gate)──> [Level 1: Controlled Human Gate] ──(Sign-Off)──> [Level 2: Direct Publication]
   • Webhook ingested & validated                          • Operator inspects finding draft                 • Automated PR comment
   • Full AST analysis & AI review                         • Operator approves/rejects                      • STRICTLY FORBIDDEN IN PILOT
   • Adversarial Judge filtering                           • Only approved comments publish
   • Zero GitHub comments created                          • Commit drift aborts publication
   • Telemetry logged to database
```

### Invariants Enforced in Shadow Mode:
1. `PUBLISHING_ENABLED=false`: Webhook events trigger AST parsing, agent review, and Adversarial Judge evaluation, but GitHub comment publishing endpoints are short-circuited.
2. `COMMIT_SHA_EXACT_MATCH`: The reviewed commit SHA must strictly match the pull request head SHA at the instant of analysis.
3. `UNTRUSTED_INPUT_ISOLATION`: Repository source code and diff content are wrapped in immutable data boundary tags (`<<<UNTRUSTED DATA: ...>>>`). Under no circumstances is LLM output executed as code.
4. `MCP_POLICY_ENFORCEMENT`: The Model Context Protocol (MCP) Sentinel tool server enforces strict tool allowlisting; dangerous operations (`execute_shell`, `modify_filesystem`, `access_environment_variables`) are permanently blocked.
5. `TENANT_ISOLATION`: All database queries and caching keys are namespaced by `installation_id` and `repository_id`. Cross-tenant data leakage is structurally impossible.

---

## 5. Controlled Publication Gate (When Authorized)

If and when a repository owner authorizes Level 1 (Human-Gated Publication), the review must satisfy all 10 pre-flight validation gates before any comment is posted to GitHub:

1. **Repository Authorization Check**: Verify repository is explicitly listed in `PILOT_AUTHORIZED_REPOSITORIES`.
2. **Head SHA Integrity**: Confirm `pr.head_sha == review.target_commit_sha`.
3. **Commit Drift Check**: If a developer pushes a new commit during review, immediately invalidate the draft and abort publication.
4. **Diff Boundary Re-Validation**: Verify that every cited comment line falls strictly within the newly changed line hunks of the current commit diff (Adversarial Judge Gate 1).
5. **Deduplication Check**: Check composite idempotency key (`repo_id:pr_id:head_sha:finding_hash`) against database to prevent duplicate comments.
6. **Factuality & Actionability Check**: Ensure finding includes valid file path, line number, code snippet evidence, and concrete remediation advice.
7. **Human Approval Authentication**: Require human operator approval with verified RBAC role (`reviewer` or `admin`). Anti-self-approval rule prevents PR author from approving their own review.
8. **Rate Limit Buffer**: Check GitHub API rate limit status; delay publication if remaining quota is under 100 requests.
9. **Single Review Envelope**: Publish comments atomically using the GitHub Pull Request Review API rather than individual unbundled comments.
10. **Immutable Audit Logging**: Write publication event to append-only audit log with sanitized payloads.

---

## 6. Safety, Reliability & Stop Conditions

The pilot must be immediately paused or terminated upon encountering any of the following **Emergency Stop Conditions**:

- **Stop Condition 1 (Data Leakage)**: Any observation of repository code, metadata, or comments leaking across tenant boundaries.
- **Stop Condition 2 (Secret Exposure)**: Any API key, token, or secret displayed in review comments, dashboard logs, or exception traces.
- **Stop Condition 3 (Approval Bypass)**: A review comment published without passing through the required human approval gate or after commit drift.
- **Stop Condition 4 (Sandbox Escape / Execution Attempt)**: An LLM-generated suggestion triggering unauthorized tool execution on the server.
- **Stop Condition 5 (Spam / Alert Fatigue Spike)**: More than 3 false-positive findings generated on a single pull request, or developer rejection rate exceeding 25%.
- **Stop Condition 6 (System Reliability Degradation)**: Upstream Gemini API 429 rate-limiting exceeding 5% of requests, or review processing latency exceeding 180s (P95).

### Emergency Incident Response Procedure:
1. **Activate Emergency Kill-Switch**: Set environment variable `CODEGUARD_KILL_SWITCH=true` and restart API service. This halts all ingestion and worker processing instantly.
2. **Revoke Webhook Credentials**: Rotate GitHub App webhook secret to reject incoming deliveries.
3. **Drain Celery Queues**: Flush Redis queue `celery` using `redis-cli flushdb`.
4. **Preserve Audit Telemetry**: Export audit logs to local incident archive for forensic analysis.
5. **Issue Stakeholder Notification**: Notify repository owners and engineering leadership within 1 hour.

---

## 7. Pilot Execution Status

$$\mathbf{PILOT\ STATUS:\ PILOT\ NOT\ EXECUTED\ —\ NO\ REAL-WORLD\ PILOT\ EVIDENCE}$$

* **Reason**: No customer repositories have been authorized for external access, and host Docker daemon is offline.
* **Next Action**: Execute Phase 23 Findings Remediation and Release-Candidate Qualification based on existing empirical test, benchmark, and operational evidence.
