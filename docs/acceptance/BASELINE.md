# CodeGuard AI — Acceptance Baseline Specification

**Document Version**: 1.0.0  
**Generated At**: 2026-09-16T15:35:00Z  
**Branch**: `main`  
**Git Commit**: `8cf3c82c056e69b92734cb2b66547749e0989e87`  
**Evaluation Phase**: Final Acceptance, Production-Simulation, and Evidence-Certification

---

## 1. System & Runtime Baseline

| Component | Version / Specification | State / Verification |
|---|---|---|
| **Operating System** | Microsoft Windows [Version 10.0.26100.3194] | Host runtime |
| **Python** | 3.13.14 (tags/v3.13.14:b09a633) | `.venv` active, 64-bit |
| **Node.js** | v24.20.0 | Active runtime |
| **Package Manager (JS)**| npm 11.19.0 | Active package manager |
| **Docker Engine** | Docker CLI 29.5.3 (build d1c06ef) | Daemon inactive |
| **Database Engine** | SQLite 3.45.3 (built-in) / PostgreSQL via psycopg2-binary 2.9.13 | SQLAlchemy 2.0.52 active |
| **Cache / Queue Broker**| Redis client 8.1.0 / Fakeredis 2.38.0 | Degradation fallback active |
| **Git** | 2.53.0.windows.1 | Clean working tree for core code |

---

## 2. Application Component Versions

| Application / Package | Version | Path / Location | Verification State |
|---|---|---|---|
| `codeguard-api` | 0.1.0 | `apps/api` | FastAPI 0.141.1, Pydantic 2.13.5 |
| `codeguard-web` | 0.1.0 | `apps/web` | Next.js 15.2.0, React 19.0.0, TypeScript 5.8.2 |
| `codeguard-mcp-server`| 0.1.0 | `apps/mcp-server` | FastMCP / Starlette 1.6.0 |
| `code-intelligence` | 0.1.0 | `packages/code-intelligence` | Tree-sitter 0.26.0 (py, js, ts) |
| `evaluation-suite` | 1.0.0 | `evaluation/` | 12 Empirical benchmark scenarios (v1) |

---

## 3. External Integration & Dependency Status

| Integration | Configuration Status | Operational Mode | Acceptance Handling |
|---|---|---|---|
| **Google Gemini API** | NOT CONFIGURED (`GEMINI_API_KEY` unset) | Fallback to `MockLLMProvider` for deterministic testing | Remote API calls marked `NOT TESTED — DEPENDENCY UNAVAILABLE` |
| **GitHub App Integration** | NOT CONFIGURED (`GITHUB_APP_ID`, `GITHUB_PRIVATE_KEY` unset) | Webhook HMAC-SHA256 signature verification & replay cache active | Live GitHub publication marked `NOT TESTED — DEPENDENCY UNAVAILABLE` |
| **PostgreSQL Cluster** | Local cluster inactive on port 5432 | Native SQLite engine with connection pool & Alembic migrations | Clean migration & rollback verified on SQLite staging DB |
| **Redis Broker** | Local Redis inactive on port 6379 | `CELERY_TASK_ALWAYS_EAGER=true`, Fakeredis fallback | Queue idempotency & degradation verified |
| **MCP Sentinel Policy** | CONFIGURED & ACTIVE | Sentinel policy engine with 4 risk tiers | 9 dangerous tools blocked, schemas verified |
| **Evaluation Framework** | CONFIGURED & ACTIVE | 12 ground-truth scenarios with regression analysis | 100% precision, 100% recall verified |

---

## 4. Test Suite Baseline Summary

- **Unit & Integration Tests**: 172 passed, 0 failed (163 in `apps/api/tests`, 9 in `apps/mcp-server/tests`).
- **Static Code Analysis**: Ruff 0.16.7: 0 errors across entire repository.
- **Frontend Type Safety**: TypeScript 5.8.2: 0 type errors across Next.js application (`tsc --noEmit`).
- **Empirical Benchmark**: 12 scenarios evaluated (F1: 1.0000, Precision: 100.0%, Recall: 100.0%, Regressions: 0).
- **Master Release Gate**: Phase 12 verification (`verify_phase12.py`) passed 22/22 dimensions.
