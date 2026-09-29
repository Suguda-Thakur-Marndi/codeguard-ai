# CodeGuard AI — Phase 19: Prioritized Action Register & Next Iteration Plan

**Document ID**: `DOC-PP-ACTIONS-01`  
**Application Version**: `1.0.0`  
**Base Commit**: `085615eb45da36135a7374b614e3705ad9ca2468`  
**Audit Date**: 2026-09-29  

---

## 1. Action Prioritization Principles

In accordance with Phase 19 Section 12 guidelines:
1. **Safety, Security & Data Integrity First**: Actions resolving architectural boundaries, zero-trust controls, and reproducible defects take precedence over convenience features.
2. **Empirical Evidence Driven**: Work is prioritized strictly based on verified evidence gaps identified in Phase 19 (e.g., absence of live pilot telemetry, host container offline).
3. **No Speculative Feature Engineering**: No ad-hoc business logic or unverified UX features are scheduled.
4. **Human Approval Mandate**: High-consequence deployment and customer onboarding actions require explicit human owner approval before execution.

---

## 2. Prioritized Action Register

### Action ACT-01: Formal Customer Pilot Charter & Repository Scope Agreement
- **Priority**: **P0 (Critical Blocker)**
- **Motivating Evidence / Gap**: Section 2 Pilot Evidence Gate determined **NO PILOT EVIDENCE** exists; release decision is held at **MORE EVIDENCE REQUIRED**.
- **Required Change**: Prepare and execute a formal Pilot Agreement with 2–3 partner engineering teams defining repository access scopes, evaluation timeline (4 weeks), and human review gates.
- **Risk Addressed**: Legal liability, unauthorized repository access, and undefined pilot success metrics.
- **Dependencies**: Legal review of data processing terms and GitHub App permission scopes.
- **Acceptance Criteria**: Signed pilot charter defining participating repositories, expected PR volume, and human feedback leads.
- **Regression Tests**: N/A (Organizational / Legal milestone).
- **Responsible Role**: Architect Agent / Product Owner.
- **Explicit Owner Approval Needed**: **YES (MANDATORY)**.

---

### Action ACT-02: Linux Container Cluster Provisioning & gVisor Sandbox Activation
- **Priority**: **P1 (High)**
- **Motivating Evidence / Gap**: Phase 16 Gate 31 reported host Docker daemon offline on local Windows development machine; Linux kernel sandboxing was unverified.
- **Required Change**: Provision a dedicated staging Linux Kubernetes or Docker engine cluster running `apps/api`, `apps/mcp-server`, `apps/web`, and Celery worker with gVisor / seccomp execution sandbox.
- **Risk Addressed**: Kernel-level container escape or resource exhaustion during untrusted code intelligence AST parsing.
- **Dependencies**: Linux host provisioning; Docker Compose / Helm charts in `docker/`.
- **Acceptance Criteria**: All 4 services healthy via container health probes; `curl -f http://<staging-ip>:8000/ready` returns 200 OK.
- **Regression Tests**: `verify_phase16.py` Gate 01 and Gate 20.
- **Responsible Role**: DevOps Agent.
- **Explicit Owner Approval Needed**: **YES**.

---

### Action ACT-03: Real-Time Review Quality & Telemetry Ingestion Pipeline
- **Priority**: **P1 (High)**
- **Motivating Evidence / Gap**: Quality evaluation revealed that real-world developer acceptance and false-positive complaint rates are currently unmeasured.
- **Required Change**: Wire Prometheus metrics and structured log emitters for: review start-to-finish latency, specialist candidate counts, judge rejection counts by gate, and developer resolution status.
- **Risk Addressed**: Inability to detect model degradation, prompt drift, or false-positive spikes during the pilot.
- **Dependencies**: Celery worker telemetry hooks in `apps/api/app/workers/tasks.py`.
- **Acceptance Criteria**: Grafana / CloudWatch dashboard displaying live P50/P95 latencies and judge rejection distributions.
- **Regression Tests**: `test_failure_recovery.py`, `test_orchestrator.py`.
- **Responsible Role**: Backend Agent / DevOps Agent.
- **Explicit Owner Approval Needed**: No.

---

### Action ACT-04: Developer Inline Feedback & Reaction Webhook Processing
- **Priority**: **P2 (Medium)**
- **Motivating Evidence / Gap**: Feedback analysis indicated that while webhook endpoints exist, active correlation of GitHub comment reactions to specific AI specialist findings needs verification.
- **Required Change**: Ensure `pull_request_review_comment` reaction webhooks (`+1`, `-1`, `confused`) update the corresponding `ReviewFinding` record in PostgreSQL with developer sentiment.
- **Risk Addressed**: Missing developer sentiment signals to calibrate specialist prompt instructions.
- **Dependencies**: GitHub App webhook subscription to `pull_request_review_comment`.
- **Acceptance Criteria**: Emitting a `-1` reaction on GitHub updates finding `developer_feedback` field to `DISMISSED` within 5 seconds.
- **Regression Tests**: `test_webhooks.py`.
- **Responsible Role**: Backend Agent.
- **Explicit Owner Approval Needed**: No.

---

### Action ACT-05: Real-World Multi-Language Benchmark Dataset Expansion (Dataset `v2`)
- **Priority**: **P2 (Medium)**
- **Motivating Evidence / Gap**: Current benchmark dataset ($N=12$) is limited to curated synthetic samples; larger sample size required for statistical significance.
- **Required Change**: Curate 50 real-world, anonymized pull requests across Python, TypeScript, Go, and Java with expert human-labeled ground truth defects.
- **Risk Addressed**: Overfitting specialist prompts to the 12 existing synthetic test cases.
- **Dependencies**: Selection of permissive open-source repositories (Apache 2.0 / MIT).
- **Acceptance Criteria**: Benchmark suite evaluates 50 scenarios with stratified precision/recall reporting.
- **Regression Tests**: `benchmark.py`, `test_evaluation.py`.
- **Responsible Role**: Code Intelligence Agent / Testing Agent.
- **Explicit Owner Approval Needed**: No.

---

### Action ACT-06: Gemini API Token Quota & Circuit Breaker Optimization
- **Priority**: **P2 (Medium)**
- **Motivating Evidence / Gap**: Theoretical cost calculations ($0.09 for 12 runs) need replacement with live API quota monitoring and hard expenditure caps.
- **Required Change**: Implement a daily token expenditure ceiling in `apps/api/app/core/config.py` that pauses automatic review queueing if daily budget is exceeded.
- **Risk Addressed**: Runaway API billing during unexpected webhook floods or denial-of-wallet attacks.
- **Dependencies**: Redis daily usage counter.
- **Acceptance Criteria**: Review queue pauses with an alert when daily spending threshold is hit.
- **Regression Tests**: `test_llm_provider.py`.
- **Responsible Role**: Backend Agent.
- **Explicit Owner Approval Needed**: No.

---

### Action ACT-07: Static Type Annotation Hardening in Test Assertion Files
- **Priority**: **P3 (Maintenance)**
- **Motivating Evidence / Gap**: Pyright identified 66 strict type warnings across test files due to asserting `in` on nullable model attributes without explicit null guards.
- **Required Change**: Add type narrowing guards (`assert record is not None`) in test assertions across `test_symbols_and_references.py`, `test_judge.py`, and `test_webhooks.py`.
- **Risk Addressed**: Masking genuine type regressions in future test additions.
- **Dependencies**: None.
- **Acceptance Criteria**: `pyright apps/api/tests` passes with 0 errors.
- **Regression Tests**: `pytest apps/api/tests`.
- **Responsible Role**: Testing Agent.
- **Explicit Owner Approval Needed**: No.

---

### Action ACT-08: Security Red-Team Penetration Test on Cloud Ingress & Webhook Gateway
- **Priority**: **P1 (High)**
- **Motivating Evidence / Gap**: Security review noted that external cloud edge defenses (WAF, rate limiting, DDoS mitigation) remain unverified against public adversaries.
- **Required Change**: Conduct an authorized external penetration test on the deployed staging ingress endpoint testing webhook HMAC bypasses, slowloris attacks, and CORS poisoning.
- **Risk Addressed**: Cloud infrastructure compromise during production pilot.
- **Dependencies**: Completion of Action ACT-02 (Linux container deployment).
- **Acceptance Criteria**: Written red-team report confirming zero unauthorized access or ingress bypasses.
- **Regression Tests**: `verify_phase15.py` security suite.
- **Responsible Role**: Security Agent.
- **Explicit Owner Approval Needed**: **YES**.
