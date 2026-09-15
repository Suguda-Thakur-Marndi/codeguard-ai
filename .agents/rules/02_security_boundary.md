# Security Boundary & Anti-Bypass Rule

## Zero-Trust Principle

**ALL EXTERNAL INPUT IS UNTRUSTED.** This includes webhook payloads, diff bodies, branch names, PR descriptions, and AI model outputs.

## Inviolable Security Controls

1. **No Authentication Bypass**:
   - Never disable authentication middleware or token verification.
   - Any agent proposing `DEV_AUTH_BYPASS = true` in production code must be rejected immediately.
2. **No Approval Bypass**:
   - Human approval is mandatory for all high/critical findings and state-modifying actions.
   - MCP tools marked with high risk must never be executed automatically.
3. **No Direct Production Database Access**:
   - All schema changes must use Alembic migrations.
   - Raw SQL execution bypassing the repository and ORM layers is strictly forbidden.
4. **No Hardcoded Secrets**:
   - Secret tokens, private keys, and webhook secrets must be managed exclusively via environment variables and settings.
5. **AI is Untrusted Reasoning**:
   - LLM generation must always pass through the 5-gate Adversarial Judge and Pydantic validation before being persisted or published.
