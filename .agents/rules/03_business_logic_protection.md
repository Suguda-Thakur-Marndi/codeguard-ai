# Business Logic Protection Rule

## Core Business Invariants

The following domain models and workflows represent core business logic and must not be altered without formal architectural review:

1. **Review Finding Severity**:
   - `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`.
   - Severity semantics and thresholds are fixed.
2. **Approval Request Lifecycle**:
   - `PENDING -> APPROVED | REJECTED | EXPIRED`.
   - Anti-self-approval rule: PR author cannot approve their own review actions.
   - Commit-drift invalidation: If new commits are pushed, existing approvals are invalidated.
3. **Publication Integrity**:
   - GitHub publications require valid commit SHA match. Stale reviews targeting outdated commits must be blocked.
4. **Tool Risk Classification**:
   - Destructive operations (`git push --force`, `drop table`, `rm -rf`) are classified as `CRITICAL/FORBIDDEN` and must be rejected by MCP Sentinel.
