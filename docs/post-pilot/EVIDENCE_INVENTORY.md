# CodeGuard AI — Phase 19: Evidence Inventory & Telemetry Ledger

**Document ID**: `DOC-PP-EVIDENCE-01`  
**Application Version**: `1.0.0`  
**Base Commit**: `085615eb45da36135a7374b614e3705ad9ca2468`  
**Pilot Status**: **NO PILOT EVIDENCE**  
**Audit Date**: 2026-09-29  

---

## 1. Evidence Gate Statement & Taxonomy

Under the Phase 19 Pilot Evidence Gate, CodeGuard AI is classified as **NO PILOT EVIDENCE**.

To uphold the prime directives of scientific rigor, zero-trust integrity, and non-fabrication:
1. **No synthetic customer data or artificial production feedback** has been created or presented as real-world evidence.
2. All records listed below are categorized transparently by their true generation environment: **Local**, **Staging**, or **Synthetic Benchmark Fixture**.
3. Every genuine local and staging evidence source is cataloged with its exact reproduction commands, data boundaries, and known limitations.

---

## 2. Complete Inventory of Available Evidence Sources

| Evidence ID | Category | Source File / Location | Date Collected | Version / Commit | Environment | Evidence Nature | PII / Secret Risk | Independently Reproducible | Known Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **EV-UNIT-PYTEST** | Automated Unit Tests | `apps/api/tests/`, `apps/mcp-server/tests/` | 2026-09-29 | `085615e` | Local Host (Python 3.13) | Simulated / Unit Test Fixtures | None (All synthetic fixtures) | **YES**: `pytest apps/api/tests apps/mcp-server/tests -q` | Uses SQLite dialect for quick test runs; does not test physical PostgreSQL clustering. |
| **EV-ACC-01..30** | Acceptance Scenarios | `docs/acceptance/evidence/AC-*/evidence.json` | 2026-09-28 | `085615e` | Staging Acceptance Harness | Staged End-to-End Simulation | None (Synthetic PR payloads) | **YES**: `python scripts/run_acceptance_suite.py` | Uses `LLM_PROVIDER=mock`; does not make live calls to Google Gemini. |
| **EV-AUDIT-SEC** | Zero-Secret Audit | `docs/acceptance/evidence/AUDIT-SEC/evidence.json` | 2026-09-28 | `085615e` | Local Repository Scan | Static Analysis & Regex Scan | Scanned 205 files; 0 secrets discovered | **YES**: Executed as part of acceptance suite | Scans git repository tree; does not scan external cloud secret stores. |
| **EV-AUDIT-PH** | Zero-Placeholder Audit | `docs/acceptance/evidence/AUDIT-PH/evidence.json` | 2026-09-28 | `085615e` | Local Codebase Scan | Static AST & Token Scan | None | **YES**: Executed as part of acceptance suite | Scans production Python files; excludes test directories by design. |
| **EV-AUDIT-OBS** | Observability Trace | `docs/acceptance/evidence/AUDIT-OBS/evidence.json` | 2026-09-28 | `085615e` | Local In-Memory Trace | Simulated Review Lifecycle (T0-T10) | None | **YES**: Executed as part of acceptance suite | Total simulated latency 140.8ms; does not reflect internet network transit. |
| **EV-AUDIT-DB** | Clean DB Migration | `docs/acceptance/evidence/AUDIT-DB/evidence.json` | 2026-09-28 | `085615e` | Local SQLite / Alembic | Staging DB Upgrade (001-006) | None | **YES**: Executed as part of acceptance suite | Verifies 28 tables created; does not benchmark multi-terabyte schema alter times. |
| **EV-AUDIT-BK** | Backup & Restore | `docs/acceptance/evidence/AUDIT-BK/evidence.json` | 2026-09-28 | `085615e` | Local File System & SQLite | SQLite Snapshot / SHA256 Check | None | **YES**: Executed as part of acceptance suite | Tests single-file snapshot; does not test cloud block storage snapshot replication. |
| **EV-BENCH-RUN** | Empirical Benchmark | `benchmark_report.json`, `benchmark_report.md` | 2026-09-14 | `8a0f1a5` | Local Benchmark Runner | Curated Synthetic Scenarios (N=12) | None (Synthetic code repositories) | **YES**: `python benchmark.py` | N=12 scenarios; evaluates accuracy on curated samples, not wild multi-language PRs. |
| **EV-SRE-GATES** | Master SRE Suite | `verify_phase16.py` | 2026-09-29 | `085615e` | Local Host Runtime | 27 Verification Gates | None | **YES**: `python verify_phase16.py` | Validates host environment readiness; host Docker daemon was offline during run. |
| **EV-SEC-GATES** | Security Audit Suite | `verify_phase15.py` | 2026-09-28 | `74eb82d` | Local Host Runtime | 23 Security & Red-Team Gates | None | **YES**: `python verify_phase15.py` | Local execution sandbox validates AST filters; Linux gVisor requires Linux container host. |
| **EV-OPS-LOGS** | Operational Run Logs | `docs/operations/evidence/EV-*.log` | 2026-09-28 | `74eb82d` | Local Staging Environment | Staging Execution Logs | None (Scrubbed and synthetic) | **YES**: Recorded during Phase 16 execution | Captures local subsystem logs; no live cloud network telemetry. |

---

## 3. Inventory of Missing / Absent Evidence Sources

To ensure complete clarity regarding what was **NOT** collected:

1. **Live Customer Pull Request Traces**:
   - *Status*: **ABSENT** (`NOT VERIFIED`).
   - *Description*: No real pull requests from external open-source or enterprise private repositories were reviewed by a live CodeGuard AI deployment.
2. **Customer Developer Feedback & Review Reactions**:
   - *Status*: **ABSENT** (`NOT VERIFIED`).
   - *Description*: No developer inline comments, approval/rejection button clicks, or thumbs-up/down ratings from external users exist.
3. **External Production Bug Reports**:
   - *Status*: **ABSENT** (`NOT VERIFIED`).
   - *Description*: Zero external issues have been filed on GitHub or Jira by real-world pilot participants.
4. **Live Cloud Token Consumption & Billing Telemetry**:
   - *Status*: **ABSENT** (`NOT VERIFIED`).
   - *Description*: All token numbers in `benchmark_report.json` ($0.09 across 12 runs) are calculated locally using static cost formulas ($0.0025 per 1,000 tokens), not sourced from a live Google Cloud Platform billing export.
5. **Real-World Incident & Outage Reports**:
   - *Status*: **ABSENT** (`NOT VERIFIED`).
   - *Description*: No real outages or failovers occurred in customer environments because no customer infrastructure was connected.

---

## 4. Confidentiality & Data Protection Verification

1. **PII and Secret Scrubbing**:
   - Automated regex scrubbers (`app.core.logging.redact_sensitive_data`) were verified on all logged evidence files.
   - All authorization tokens (`ghp_*`, `AIzaSy*`, `Bearer *`) in tests are synthetic placeholders (e.g. `mock-secret-key-32-chars-long`).
2. **No Repository-Sensitive Leakage**:
   - All scenario code snippets in `evaluation/scenarios/` and `fixtures/` are synthesized demonstration files created specifically for unit and benchmark validation.
   - Zero proprietary customer intellectual property is stored or referenced anywhere in the repository.

---

## 5. Checklist for Collecting Pilot Evidence in a Future Authorized Run

When an authorized customer pilot is officially scheduled, the following evidence ledger must be maintained:

- [ ] **CH-01: Signed Pilot Authorization Agreement** (Documenting authorized repository scopes, user seats, and testing duration).
- [ ] **CH-02: Deployed Image Digest & Git SHA** (Exact Docker container image SHA-256 and commit hash deployed to the pilot cluster).
- [ ] **CH-03: Real Ingress Webhook Audit Log** (Cryptographically verified webhook logs with anonymized repository IDs and delivery timestamps).
- [ ] **CH-04: Review Job Execution Telemetry** (End-to-end latency distributions, agent-level token consumption, and specialist candidate findings).
- [ ] **CH-05: Adversarial Judge Filtering Records** (Counts and line numbers of candidate findings suppressed by the 5 judge gates).
- [ ] **CH-06: Human Approval & Modification Records** (Operator approvals, rejections, line modifications, and reason codes).
- [ ] **CH-07: Developer Feedback & Inline Reactions** (Explicit developer thumbs up/down, comment resolution status, and complaint tickets).
- [ ] **CH-08: Actual LLM Provider Invoices & Rate-Limit Logs** (Exact Gemini API billing telemetry and 429 quota exhaustion events).
- [ ] **CH-09: Incident & Degradation Reports** (Any worker crashes, database connection pool exhaustion, or webhook retry spikes).
