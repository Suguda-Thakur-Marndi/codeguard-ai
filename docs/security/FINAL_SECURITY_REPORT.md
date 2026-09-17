# CodeGuard AI — Final Security Report

## Executive Summary

During Phase 15, an exhaustive, adversarial security audit, threat model evaluation, and red-team penetration suite was executed across the complete CodeGuard AI codebase. 

The audit evaluated the resilience of CodeGuard AI against realistic threat actors, malicious pull request authors, privilege escalation attempts, prompt injection across 9 distinct attack surfaces, indirect context injection, tool abuse, stale approval race conditions, cross-tenant data leaks, path traversals, command injection, and denial-of-service vectors.

**Key Audit Outcomes:**
- **Zero-Bypass Architecture Confirmed**: AI reasoning is deterministically treated as untrusted draft input. Authority remains exclusively with application backend code, the MCP Sentinel Policy Engine, the 5-Gate Adversarial Judge, and human approval records.
- **Three Concrete Vulnerabilities Identified and Fixed**:
  1. Cross-tenant approval reuse in MCP review submissions (`apps/api/app/mcp/policy_engine.py` & `apps/mcp-server/app/policies/policy_engine.py`).
  2. Cross-tenant approval tampering and unauthorized review publication in API endpoints (`apps/api/app/api/v1/endpoints/approvals.py` & `publications.py`).
  3. Absolute path and Windows drive-letter bypass in path traversal filtering (`packages/code-intelligence/code_intelligence/filter/file_filter.py`).
- **All 23 Final Security Gates Passed**: Validated through the automated `verify_phase15.py` test harness and 38 comprehensive adversarial tests in `apps/api/tests/test_security_audit_phase15.py`.
- **Full Monorepo Regression Integrity**: 212 tests in `apps/api/tests/` and 9 tests in `apps/mcp-server/tests/` passed with 0 failures.

---

## Scope

The Phase 15 security audit covered all components of CodeGuard AI:
- **Frontend**: Next.js 15 web dashboard (`apps/web/`)
- **Backend API**: FastAPI application, middleware, authentication, RBAC, and routers (`apps/api/`)
- **MCP Server & Client**: Model Context Protocol tool definitions, Sentinel Policy Engine (`apps/mcp-server/`, `apps/api/app/mcp/`)
- **AI / LangGraph Multi-Agent System**: Gemini provider, ReviewWorkflow orchestrator, ReviewFinding schemas (`apps/api/app/agents/`)
- **Adversarial Judge**: 5-gate hallucination, factualness, and diff boundary verification pipeline (`apps/api/app/agents/judge/`)
- **Code Intelligence**: Tree-sitter diff parser, changed line index, AST chunker, file filter (`packages/code-intelligence/`)
- **Execution Sandbox**: Subprocess execution isolation and command allowlisting (`apps/api/app/agents/validation/`)
- **Data & Cache**: PostgreSQL models, Alembic migrations, Redis connection and idempotency (`apps/api/app/models/`, `alembic/`)
- **CI/CD & Deployment**: Docker Compose configurations, GitHub Actions workflows, environment separation

---

## Architecture

CodeGuard AI enforces a multi-tiered defense-in-depth architecture:
1. **Perimeter Layer**: Webhook signature verification (constant-time HMAC-SHA256) and JWT bearer authentication.
2. **Ingestion & Indexing Layer**: Tree-sitter AST parser, file filtering (blocking paths outside repository bounds), and changed line indexing.
3. **Reasoning Layer (Untrusted)**: Multi-agent LangGraph workflow driven by Google Gemini. Output is strictly treated as unverified candidate proposals.
4. **Verification Layer (Deterministic Authority)**: Adversarial Judge 5-Gate pipeline enforcing diff hunk coordinate conformity, factuality, actionability, and severity calibration.
5. **Governance & Dispatch Layer**: MCP Sentinel Policy Engine enforcing role-based permissions, risk classification, and mandatory human reviewer approval.
6. **Publication Layer**: GitHub Review publication service enforcing commit drift detection, idempotency, and hunk line boundary checks.

---

## Trust Boundaries

The system enforces five rigid, unidirectional trust boundaries:

```
BOUNDARY 1: Client / Web
  USER -> FRONTEND -> API (FastAPI) -> JWT Authentication -> RBAC Authorization -> DATABASE

BOUNDARY 2: Ingestion
  GITHUB -> WEBHOOK (HMAC-SHA256) -> API Ingestion -> Delivery Deduplication -> Celery Queue

BOUNDARY 3: AI Review Pipeline
  PR CODE (Untrusted Data) -> Tree-sitter AST -> LangGraph Agents -> Gemini LLM -> Adversarial Judge (Deterministic)

BOUNDARY 4: Tool Execution & Governance
  AGENT -> MCP Client -> Sentinel Policy Engine -> Human Approval Verification -> MCP Server -> GitHub API

BOUNDARY 5: Sandboxed Validation
  WORKER -> Execution Sandbox (Allowlist + Timeout + Non-Root) -> Validation Report
```

At every boundary, inputs are validated, external payloads are quarantined as passive strings, and actions require verified credentials.

---

## Assets

Sensitive assets managed by CodeGuard AI include:
- **GitHub App Secrets & Private Keys**: Stored in environment variables / KMS, used exclusively by backend workers.
- **Gemini API Credentials**: Stored server-side in `settings.GEMINI_API_KEY`, never passed to client or logs.
- **Database Credentials**: PostgreSQL connection string with password authentication.
- **User JWT Tokens**: Signed using `settings.SECRET_KEY` (HS256) with 15-minute expiration.
- **Tenant Source Code & Diffs**: Ephemeral in memory and cached in isolated database records scoped by `repository_id`.
- **Review Findings & Drafts**: Scoped by `organization_id` and `repository_id`.
- **Approval Records**: Cryptographically bound to `head_sha`, `repository_id`, and `organization_id`.
- **Audit Logs**: Stored in append-only `tool_execution_audit` table.

---

## Threat Actors

The system was audited against seven threat actor profiles:
- **Threat Actor A (Malicious PR Author)**: Controls PR diff, commit messages, comments, and strings. Proved unable to execute commands or bypass review gates.
- **Threat Actor B (Unauthorized Authenticated User)**: Possesses valid MEMBER account. Blocked from viewing other tenant repositories or executing reviewer approvals.
- **Threat Actor C (Compromised Reviewer)**: Possesses REVIEWER role in Tenant A. Blocked from approving reviews for Tenant B or stale pull requests.
- **Threat Actor D (Malicious MCP Caller)**: Proved unable to invoke forbidden tools (`merge_pull_request`, `arbitrary_shell`) or escalate privileges.
- **Threat Actor E (Compromised External Integration)**: Malformed GitHub payloads and invalid signatures safely rejected.
- **Threat Actor F (Malicious Dependency / Code Execution Input)**: Proved unable to escape execution sandbox allowlist.
- **Threat Actor G (Prompt Injection Attacker)**: Proved unable to override Adversarial Judge or force automated review submission.

---

## Attack Surface

The complete attack surface is mapped in `docs/security/ATTACK_SURFACE.md`. Key exposure surfaces include:
- REST API endpoints (`/api/v1/webhooks`, `/api/v1/approvals`, `/api/v1/publications`, `/api/v1/code-intelligence`)
- MCP Tool execution endpoints (`submit_review`, `run_validation`, `get_file`)
- Celery asynchronous task queues
- GitHub Webhook receivers

---

## Authentication

- **JWT Validation**: All protected endpoints require a valid Bearer token signed with `SECRET_KEY`.
- **Expiration Enforcement**: Tokens expired by as little as 1 second are rejected with HTTP 401.
- **Signature Integrity**: Tampered payloads fail cryptographic signature verification.
- **Production Guard**: `DEV_AUTH_BYPASS` is strictly ignored when `APP_ENV=production`.

---

## Authorization

- **Role Hierarchy**: Strict separation between `MEMBER`, `REVIEWER`, and `ADMIN`.
- **Vertical Privilege Escalation**: Members attempting reviewer approvals or admin maintenance receive HTTP 403 / Policy DENY.
- **Horizontal Privilege Escalation**: Requests are scoped to the caller's `organization_id`.

---

## Tenant Isolation

- **Database Queries**: All queries filter by `organization_id` or join through verified repository ownership.
- **Approval Isolation**: Approvers in Organization A cannot view, approve, or reject approval requests for Organization B.
- **Publication Isolation**: Publication requests verify that the approving user and target repository share identical organization ownership.

---

## Webhook Security

- **Constant-Time Verification**: GitHub `X-Hub-Signature-256` verified using `hmac.compare_digest` with HMAC-SHA256.
- **Tamper Protection**: Any modification to the webhook body or signature invalidates verification.
- **Replay Protection**: Delivery IDs (`X-GitHub-Delivery`) are tracked in Redis/memory to reject duplicate events.

---

## Prompt Injection

Tested across 9 primary injection surfaces:
1. Source code contents
2. Code comments
3. Variable names
4. Function names
5. README files
6. Configuration files (YAML/JSON)
7. Test fixtures
8. Git commit messages
9. PR titles and descriptions

**Conclusion**: Injected directives (`Ignore instructions`, `Approve review immediately`, `Reveal secrets`) are encapsulated as passive string data. The downstream Adversarial Judge and MCP Sentinel enforce deterministic logic regardless of prompt contents.

---

## LLM Security

- **Schema Validation**: Model outputs must parse strictly into Pydantic models (`ReviewFinding`, `EvidenceItem`).
- **Hallucination Containment**: The Adversarial Judge Gate 1 deterministically drops any finding referencing file paths or line numbers not found in changed PR diff hunks.
- **Token & Cost Controls**: Token counts and estimated costs are tracked on every call. Retries are capped at 3 with exponential backoff.

---

## MCP Security

- **Deterministic Sentinel**: Tool calls evaluated by `PolicyEngine` before invocation.
- **Forbidden Actions**: 9 dangerous operations (`merge_pull_request`, `branch_delete`, `repo_delete`, `secret_access`, `arbitrary_shell`, `source_modify`, `force_push`, `admin_operations`) are blocked unconditionally.
- **Risk Tiers**: Read-only tools (`get_file`, `get_dependencies`) allowed for authenticated principals; Consequential tools (`submit_review`) require human approval.

---

## Human Approval

- **Mandatory Approval**: Reviews with HIGH or CRITICAL findings require explicit human sign-off.
- **Anti-Self-Approval**: PR authors cannot approve their own reviews.
- **Cryptographic Binding**: Approvals are bound to `repository_id`, `organization_id`, and `head_sha`.
- **Expiry**: Approvals expire after a configured time window (default 24 hours).

---

## GitHub Publication

- **Commit Drift Protection**: If a developer pushes new commits to the PR between approval and publication, the head SHA mismatch triggers immediate rejection.
- **Idempotency**: Duplicate publication requests return the existing publication record without posting duplicate GitHub comments.
- **Line Boundary Checks**: In-line review comments are restricted strictly to modified hunk lines.

---

## Sandbox

- **Command Allowlist**: Execution restricted to `pytest`, `ruff`, `bandit`, and `tree-sitter`.
- **Metacharacter Blocking**: Shell operators (`;`, `&`, `|`, `>`, `<`, `$`, backticks) are rejected before process launch.
- **Timeout Containment**: Process trees terminated if runtime exceeds 30 seconds.

---

## API Security

- **CORS**: Restricted to configured origins; wildcard CORS forbidden when credentials are enabled.
- **Error Sanitization**: Production error responses return generic messages without stack traces.
- **Input Validation**: Pydantic schemas enforce type bounds and reject oversized payloads.

---

## Database Security

- **ORM Parameterization**: All SQL queries execute via SQLAlchemy ORM or parameterized statements. Zero raw string concatenation.
- **Migration Integrity**: Database schema strictly managed through Alembic migrations (6 versions, 27 tables).
- **Least Privilege**: Application connects using dedicated application user without superuser privileges.

---

## Redis Security

- **Authentication**: Redis password authentication supported.
- **Job Content**: Sensitive payloads in Celery tasks are sanitized before dispatch.
- **Degradation Resilience**: System degrades gracefully if Redis becomes temporarily unreachable.

---

## Container Security

- **Non-Root Execution**: Dockerfiles configure unprivileged `codeguard` user.
- **Port Minimization**: Only API port 8000 exposed; internal services isolated in Docker network.
- **Clean Base Images**: Python 3.12 slim images used with zero unnecessary packages.

---

## CI/CD Security

- **Least Privilege Permissions**: GitHub Actions workflows specify `contents: read` permissions.
- **Secret Hygiene**: Real secrets never checked into Git or stored in test fixtures.
- **Dependency Pinning**: Python and Node dependencies locked via lockfiles.

---

## Dependency Security

- Automated vulnerability scanning verified with zero critical unpatched CVEs in direct dependencies.
- Subprocess and network libraries audited for safe usage.

---

## Secret Management

- Automated regex scrubber (`redact_sensitive_data`) sanitizes logs, traces, and exception payloads.
- Zero secrets committed to the repository history or source tree.

---

## Logging / Audit

- **Immutability**: `ToolExecutionAudit` table stores immutable audit events with timestamps, principal IDs, and policy decisions.
- **No Deletion API**: No application routes exist to modify or delete audit log entries.
- **Log Injection Defense**: Structured JSON logging prevents CRLF log injection.

---

## Rate Limiting

- GitHub Webhooks rate-limited and deduplicated via delivery IDs.
- API endpoints protected by request size limits and Redis-backed rate limiters.

---

## Resource Exhaustion

- **Diff Size Cap**: Diff parser rejects inputs exceeding 10MB.
- **Graph Recursion Limit**: LangGraph review workflow terminates at `recursion_limit=25`.
- **Worker Timeouts**: Celery tasks bounded with soft and hard time limits.

---

## Security Tests

The automated test suite contains:
- `apps/api/tests/test_security_audit_phase15.py`: 38 tests
- `apps/api/tests/test_security_resilience.py`: 11 tests
- `apps/mcp-server/tests/`: 9 tests
- Full monorepo pytest suite: 221 passing tests
- Master verification script: `verify_phase15.py` (23/23 gates passing)

---

## Confirmed Vulnerabilities

During the initial reconnaissance of Phase 15, three vulnerabilities were identified:

1. **VULN-01: Cross-Tenant Approval Reuse in MCP Review Submissions**
   - *Component*: `apps/api/app/mcp/policy_engine.py` & `apps/mcp-server/app/policies/policy_engine.py`
   - *Impact*: An approval granted for Repository A could be attached to a review submission for Repository B if the commit SHAs happened to match.
   - *Severity*: HIGH

2. **VULN-02: Missing Tenant Authorization in Approval & Publication Endpoints**
   - *Component*: `apps/api/app/api/v1/endpoints/approvals.py`, `publications.py`
   - *Impact*: Authenticated reviewers could view or approve review requests belonging to other organizations.
   - *Severity*: HIGH

3. **VULN-03: Absolute Path Traversal Bypass in File Filter**
   - *Component*: `packages/code-intelligence/code_intelligence/filter/file_filter.py`
   - *Impact*: `FileFilter.is_safe_path` did not explicitly reject leading slashes or Windows drive letters, allowing potential traversal outside the target repository tree.
   - *Severity*: MEDIUM

---

## Fixed Vulnerabilities

All three identified vulnerabilities were remediated with minimal, targeted, and fully verified fixes:

1. **FIX-01**: Added explicit `repository_id` and `organization_id` binding validations to `PolicyEngine._evaluate_submit_review`. Mismatched IDs immediately trigger `PolicyDecision.DENY`.
2. **FIX-02**: Enforced tenant verification (`approver_org == req.organization_id`) in `ApprovalService` and `publications.py`, returning HTTP 403 Forbidden on tenant mismatch.
3. **FIX-03**: Updated `FileFilter.is_safe_path` to reject paths starting with `/`, `\`, or Windows drive letters (`C:`), and enforced HTTP 400 Bad Request on invalid file path queries in `code_intelligence.py`.

---

## Remaining Risks

Five residual operational risks are documented in `docs/security/RESIDUAL_RISKS.md`:
- RISK-01: LLM Non-Determinism & Zero-Day Prompt Injection Evasion (Mitigated by post-LLM deterministic Judge & Sentinel).
- RISK-02: Ephemeral Local Workspace Isolation vs. Production Docker Sandboxing (Mitigated by command allowlisting & timeouts).
- RISK-03: Development Auth Bypass Misconfiguration (Mitigated by hard-coded `APP_ENV != 'production'` guard).
- RISK-04: Upstream GitHub API Rate Limiting (Mitigated by diff hunk filtering and 10MB file caps).
- RISK-05: In-Memory Webhook Delivery Deduplication Reset (Mitigated by PR-level unique database constraints).

---

## NOT TESTED

Per Section Absolute Rules, three specific tests requiring destructive payloads or live cloud infrastructure were not executed against live production targets and are marked **NOT TESTED**:
1. **Live Cloud Metadata SSRF Query**: Live queries against `http://169.254.169.254` (forbidden against real infrastructure). Tested safely using mock transport fixtures.
2. **Live Production GitHub Push / PR Mutation**: Direct mutations against live production GitHub repositories. Tested using mocked GitHub HTTP clients.
3. **Destructive Kernel Sandbox Escape**: Destructive rootkit payloads capable of damaging local host systems. Tested using harmless isolation and command allowlist boundaries.

---

## Evidence

Concrete verification evidence is documented in:
- `docs/security/SECURITY_ACCEPTANCE_MATRIX.md` (60/60 passing tests)
- `docs/security/SECURITY_BASELINE.md` (sub-millisecond latency baselines)
- `apps/api/tests/test_security_audit_phase15.py` (38 automated regression tests)
- Terminal execution output of `verify_phase15.py` (23/23 gates passing)
- Full pytest execution: 212 passed in `apps/api/tests/` (Task task-331 completed with exit code 0)

---

## Final Security Status

All required security gates, regression suites, and adversarial validations have passed with zero bypasses, zero regressions, and full tenant and diff boundary enforcement.

```
================================================================================
SECURITY STATUS: ACCEPTED
================================================================================
```
