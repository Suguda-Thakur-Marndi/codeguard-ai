# Context7 Version Safety & Documentation Rule

## Version-Safe Library Integration

When working with third-party libraries (FastAPI, Pydantic, SQLAlchemy, Redis, Celery, LangGraph, Google GenAI, Next.js, React, Tailwind):

1. **Check Manifests First**:
   - Inspect `apps/api/pyproject.toml` or `apps/web/package.json` to verify the currently pinned version.
   - Never write code targeting newer major/minor API signatures without verifying installed versions.
2. **Retrieve Authoritative Docs**:
   - Use Context7 to fetch official documentation, parameter types, and deprecation notices for the *installed version*.
3. **No Spontaneous Upgrades**:
   - Do NOT bump dependencies in `pyproject.toml` or `package.json` simply because Context7 documentation mentions a newer feature.
4. **Resolution of Discrepancies**:
   - If library documentation recommends an approach that disrupts existing CodeGuard architecture, the project architecture takes precedence.
