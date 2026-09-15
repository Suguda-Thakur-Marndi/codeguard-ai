# Serena Codebase Investigation Rule

## 11-Step Codebase Safety Workflow

Prior to modifying any existing symbol, class, method, or service:

1. **Identify Target**: Define the functional area requiring modification.
2. **Locate Symbols**: Use AST and language parser tools to locate relevant classes, functions, and models.
3. **Inspect Definition**: Read the exact definition, types, and docstrings.
4. **Inspect Callers**: Discover all call sites across the codebase to assess impact.
5. **Inspect Dependencies**: Map incoming and outgoing module dependencies.
6. **Understand Existing Patterns**: Identify conventions used in neighboring code.
7. **Identify Minimal Change**: Formulate the smallest surgical diff that satisfies the task.
8. **Implement**: Write code conforming to existing patterns.
9. **Run Targeted Tests**: Verify the specific component with unit tests.
10. **Re-inspect Affected Symbols**: Verify that caller contracts remain intact.
11. **Run Integration Tests**: Confirm full end-to-end compatibility.

Agents must not guess symbol signatures or blindly modify code based on names alone.
