---
name: codeguard-serena-navigator
description: >-
  Codebase-aware engineering navigation instructions using AST, symbols,
  and dependency graphs powered by CodeGuard's code-intelligence engine.
---

# Serena Codebase Navigator

This skill guides deep codebase navigation, symbol discovery, and dependency tracing before making code changes.

## Capabilities

1. **Symbol Discovery**: Locating classes, functions, models, and type definitions using AST parsing rather than raw text search.
2. **Call Site Mapping**: Finding all callers of a method to evaluate regression blast radius.
3. **Dependency Graph Resolution**: Tracing imports and cross-module dependencies across `apps/api`, `apps/mcp-server`, and `packages/`.
4. **Context Retrieval**: Extracting surrounding code context and type signatures for targeted refactoring.

## 11-Step Investigation Procedure

```text
1. Identify Target Functionality
          ↓
2. Locate Symbols (AST)
          ↓
3. Inspect Definitions & Types
          ↓
4. Inspect Callers & Usages
          ↓
5. Inspect Dependencies
          ↓
6. Understand Existing Patterns
          ↓
7. Identify Minimal Change
          ↓
8. Implement Minimal Edit
          ↓
9. Run Targeted Unit Tests
          ↓
10. Re-inspect Affected Callers
          ↓
11. Run Integration Test Suite
```

Always use targeted codebase context. Avoid injecting entire files into agent contexts when specific symbols and callers suffice.
