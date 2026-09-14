# CodeGuard AI — Agentic GitHub Pull Request Review Platform

> **Phase 2 — Code Intelligence Engine**  
> *Deterministic AST semantic expansion, symbol resolution, repository dependency graphs, and token-budgeted context ranking.*  
> *(Note: LLM agents, Gemini API, LangGraph, and MCP are intentionally NOT enabled in Phase 2. Phase 2 outputs deterministic code intelligence for future AI review agents.)*

CodeGuard AI transforms raw GitHub Pull Request diffs and repository source code into structured, semantically meaningful code intelligence. By parsing code into Tree-sitter Concrete/Abstract Syntax Trees, deterministically mapping diff hunks to enclosing semantic entities (functions, methods, classes), and resolving cross-file references and dependencies in a PostgreSQL-backed repository graph, CodeGuard AI delivers high-precision context for automated code reviews.

---

## Architecture Overview

```mermaid
flowchart TD
    PR[GitHub Pull Request] --> RawDiff[Raw Unified Diff]
    RawDiff --> UDP[UnifiedDiffParser]
    UDP --> ChangedFiles[Changed Files & Hunks]
    UDP --> LineIndex[ChangedLineIndex: LEFT vs RIGHT]
    
    ChangedFiles --> SourceProv[RepositorySourceProvider]
    SourceProv --> TS[Tree-sitter Language Parsers\nPython | JavaScript | TypeScript]
    
    TS --> ASTMapper[DiffToASTMapper: Changed Line -> Enclosing AST Chunk]
    TS --> SymExt[Symbol Extractor]
    TS --> ImpExt[Import & Dependency Extractor]
    
    SymExt --> RefRes[Static ReferenceResolver]
    ImpExt --> RefRes
    
    RefRes --> Graph[Repository Graph: PostgreSQL Symbols, References, File Dependencies]
    
    ASTMapper --> Ranker[Deterministic ContextRanker & Token Budgeter]
    Graph --> Ranker
    
    Ranker --> API[Code Intelligence REST API]
    API --> NextJS[Engineering Dashboard & Dev Debug Console]
    API --> Phase3[Future Phase 3 AI Agents]
```

---

## Core Code Intelligence Pipeline

### 1. Unified Diff Parsing & Deterministic Line Index
- **`UnifiedDiffParser`**: Parses unified git diffs into strongly typed models (`DiffFile`, `DiffHunk`, `DiffLine`). Handles additions, deletions, renames, and binary files without regex-only fragility. Fallback recovery ensures individual broken hunks do not crash the entire review.
- **`ChangedLineIndex`**: Creates a deterministic line lookup index distinguishing:
  - **`RIGHT`**: Head file lines (additions and hunk context lines) eligible for PR inline comments.
  - **`LEFT`**: Base file lines (deletions and hunk context lines).
  - Enforces review boundaries with `is_valid_review_line(file_path, line_number, side)`.

### 2. Pluggable Tree-sitter Language Parsers
Language support uses a decoupled adapter pattern (`LanguageParser`):
- **`PythonParser`**: Tree-sitter Python adapter extracting functions, methods, classes, imports, variables, and cross-file calls.
- **`JavaScriptParser`**: Tree-sitter JavaScript adapter extracting functions, methods, classes, imports, and exports.
- **`TypeScriptParser`**: Tree-sitter TypeScript & TSX adapter extracting interfaces, types, classes, methods, functions, and exports.
- **`LanguageParserRegistry`**: Auto-detects parser from file extensions (`.py`, `.js`, `.mjs`, `.ts`, `.tsx`).

### 3. Diff &rarr; AST Semantic Mapping
Given an added line in a PR diff (e.g. `src/payment.py:143`), the `DiffToASTMapper` identifies the smallest enclosing semantic entity:
```
Changed Line (L143)
       │
       ▼
Method (PaymentService.refund, L130-L160)
       │
       ▼
Class (PaymentService, L20-L220)
       │
       ▼
Module (src/payment.py)
```
Generates `ASTChunk` models complete with start/end byte offsets, line spans, signatures, parameters, and attached changed line numbers.

### 4. Cross-file Reference Resolution & Repository Graph
- **`ReferenceResolver`**: Statically discovers caller-callee and inheritance relationships across files using import mappings and unique symbol lookups. If a symbol call cannot be resolved confidently, it is marked unresolved rather than hallucinating targets.
- **`RepositoryGraphBuilder`**: Constructs a directed dependency graph persisted in PostgreSQL:
  - **Nodes**: `Repository`, `File`, `Class`, `Function`, `Method`, `Interface`, `Type`.
  - **Edges**: `IMPORTS`, `CALLS`, `REFERENCES`, `INHERITS`, `IMPLEMENTS`, `DEFINES`.
  - Normalized database tables: `repository_indices`, `code_symbols`, `symbol_references`, `file_dependencies`.

### 5. Deterministic Context Ranking & Token Budgeting
Future LLM agents have finite token context windows. The `ContextRanker` scores and prioritizes context items deterministically:
- **`1.00`**: Target changed AST chunk
- **`0.95`**: Sibling symbols within the changed file
- **`0.85`**: Direct cross-file callers (e.g. `RefundController.handle_refund` calling `PaymentService.refund`)
- **`0.80`**: Direct dependencies (e.g. `PaymentRepository`, `AuthService`, `Payment`)
- **`0.50`**: Two-hop transitive dependencies
- **Token Budgeter**: Enforces configurable `max_files`, `max_symbols`, and `max_characters` limits.

### 6. Incremental Indexing Strategy
To avoid re-parsing repositories of 10,000+ files for each PR, the engine supports:
- **Initial Indexing**: Full repository scan at commit SHA.
- **Incremental Indexing**: Selectively re-parses only modified files in the PR diff, re-links their affected references, and preserves unchanged graph records.
- **Deletions & Renames**: Safely purges or updates graph entries for deleted or renamed files.

---

## Monorepo Layout

```
codeguard-ai/
├── apps/
│   ├── api/                      # FastAPI service, Celery worker, and Alembic migrations
│   │   ├── app/
│   │   │   ├── api/v1/endpoints/ # REST routes (repositories, code_intelligence, review_jobs)
│   │   │   ├── db/repositories/  # Data access (code_symbols, repository_indices, etc.)
│   │   │   ├── models/           # SQLAlchemy ORM models
│   │   │   ├── schemas/          # Pydantic v2 schemas
│   │   │   ├── services/         # CodeIntelligenceService, ReviewJobService
│   │   │   └── workers/          # Celery background worker
│   │   ├── alembic/              # Migrations 001 (core) and 002 (code intelligence)
│   │   ├── tests/                # 61 comprehensive unit & integration tests
│   │   └── Dockerfile
│   │
│   └── web/                      # Next.js 15 App Router engineering dashboard
│       ├── app/
│       │   ├── dashboard/        # System health and review metrics
│       │   ├── repositories/     # Repo list with Index Status & "Index Repository" trigger
│       │   ├── pull-requests/    # PR list & detail view with Code Intelligence flow
│       │   └── debug/            # Platform Developer Debug Console
│       ├── components/           # UI components
│       └── lib/                  # Typed API client
│
├── packages/
│   └── code-intelligence/        # Production Tree-sitter & AST intelligence engine
│       ├── code_intelligence/
│       │   ├── ast/              # DiffToASTMapper
│       │   ├── context/          # ContextRanker & Budgeting
│       │   ├── diff/             # UnifiedDiffParser & ChangedLineIndex
│       │   ├── filter/           # FileFilter (security, binary, size limits)
│       │   ├── graph/            # RepositoryGraph & Builder
│       │   ├── languages/        # Pluggable Tree-sitter adapters (Python, JS, TS)
│       │   ├── references/       # Static ReferenceResolver
│       │   ├── source/           # RepositorySourceProvider
│       │   ├── engine.py         # CodeIntelligenceEngine
│       │   └── models.py         # Pydantic typed intelligence models
│       └── pyproject.toml
│
├── fixtures/                     # Realistic multi-file test repositories
│   ├── python_repo/              # Payment service, repository, auth, controller, tests
│   ├── javascript_repo/          # JS classes, functions, and imports
│   └── typescript_repo/          # TS interfaces, types, classes, and gateways
│
├── docker-compose.yml            # Multi-container orchestration (API, worker, web, postgres, redis)
├── verify_phase2.py              # End-to-end real-world verification script
└── README.md
```

---

## Database Schema (Phase 2 Additions)

Phase 2 adds 4 database tables via Alembic migration `002_phase2_code_intelligence_tables`:

1. **`repository_indices`**:
   - `repository_id`, `commit_sha`, `status` (`NOT_INDEXED`, `INDEXING`, `READY`, `PARTIAL`, `FAILED`)
   - `files_processed`, `files_failed`, `error_count`, `index_started_at`, `index_completed_at`
2. **`code_symbols`**:
   - `repository_id`, `commit_sha`, `file_path`, `name`, `kind`, `language`
   - `start_line`, `end_line`, `signature`, `return_type`, `parent_symbol`, `source_code`
3. **`symbol_references`**:
   - `repository_id`, `commit_sha`, `source_file`, `source_symbol`, `target_file`, `target_symbol`
   - `line_number`, `reference_type` (`CALL`, `IMPORT`, `INHERITANCE`, `IMPLEMENTATION`), `resolved`
4. **`file_dependencies`**:
   - `repository_id`, `commit_sha`, `source_file`, `target_file`, `dependency_type`, `is_external`

---

## REST API Reference (Phase 2 Additions)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/repositories/{id}/index` | Inspect current repository indexing state and commit |
| `POST` | `/api/v1/repositories/{id}/index` | Trigger repository indexing at specified commit SHA |
| `GET` | `/api/v1/repositories/{id}/symbols` | Query indexed symbols (paginated, kind & file filters) |
| `GET` | `/api/v1/repositories/{id}/symbols/{symbol_id}` | Retrieve specific symbol details |
| `GET` | `/api/v1/repositories/{id}/files/{path}/symbols` | Retrieve all symbols defined in a file |
| `GET` | `/api/v1/repositories/{id}/files/{path}/dependencies`| Retrieve static imports and dependencies of a file |
| `GET` | `/api/v1/repositories/{id}/context` | Query token-budgeted ranked context for a changed file/symbol |
| `GET` | `/api/v1/review-jobs/{id}/diff` | Retrieve parsed unified diff files and hunks |
| `GET` | `/api/v1/review-jobs/{id}/chunks` | Retrieve AST semantic chunks covering changed lines |
| `GET` | `/api/v1/review-jobs/{id}/changed-lines` | Retrieve deterministic changed line index (LEFT vs RIGHT) |

---

## Security & Protection Guards

1. **Path Traversal Protection**: All paths are validated against directory traversal attacks (e.g. `../../etc/passwd`). Violations raise immediate errors and reject the operation.
2. **Binary File Skipping**: Content is checked for binary null bytes and high non-printable byte density. Marked `SKIPPED_BINARY` and excluded from Tree-sitter parsing.
3. **Large File Protection**: Threshold limits enforce maximum file size (500 KB), maximum source lines (5,000 lines), and maximum AST nodes (20,000 nodes). Large files record structured `ParserDiagnostic` records without crashing.
4. **Source Code Secrecy in Logs**: Full source code, complete diffs, and raw credentials are NEVER output to application logs.

---

## Verification & Testing

Run all 61 automated tests:
```bash
.venv\Scripts\pytest apps/api/tests -v
```

Run code formatting and lint verification:
```bash
.venv\Scripts\ruff check apps/api packages/code-intelligence
```

Run the real-world end-to-end verification script:
```bash
.venv\Scripts\python verify_phase2.py
```

Build the Next.js engineering dashboard:
```bash
cd apps/web && npm run build
```

---

## Supported Languages & Known Limitations

### Supported in Phase 2
- **Python** (3.8 - 3.13): Functions, methods, classes, variables, imports, calls, inheritance.
- **JavaScript** (ES6+): Functions, arrow functions, methods, classes, imports, exports.
- **TypeScript & TSX**: Functions, methods, classes, interfaces, type aliases, imports, exports.

### Known Limitations (Planned for Future Phases)
- **Dynamic Reflection**: Dynamically computed imports (e.g. `importlib.import_module`, `require(variable)`) are marked unresolved.
- **Full Type Inference**: Static cross-file references resolve by symbol and file dependency paths rather than a full LSP semantic compiler server.
- **C/C++, Go, Rust, Java**: Language adapter architecture is pluggable; additional Tree-sitter grammars will be added in subsequent phases.
