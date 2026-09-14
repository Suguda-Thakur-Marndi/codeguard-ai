"""Deterministic Risk Router selecting specialist review agents based on comprehension output."""

from app.agents.schemas.comprehension import ComprehensionResult


class RiskRouter:
    """Deterministic routing engine determining which specialist agents to execute."""

    @classmethod
    def route(
        cls,
        comprehension: ComprehensionResult,
        changed_files: list[str],
    ) -> tuple[list[str], str]:
        """
        Determines the exact list of specialist agents to execute.
        Returns: (selected_specialists, routing_reason)
        """
        # 1. Documentation-only PR
        doc_extensions = {".md", ".markdown", ".txt", ".rst", ".adoc"}
        all_doc_files = bool(changed_files and all(any(f.lower().endswith(ext) for ext in doc_extensions) for f in changed_files))

        if comprehension.is_documentation_only or all_doc_files:
            return [], "Documentation-only PR: skipped specialist review agents."

        selected = set()
        reasons = []

        # 2. Performance risk detected
        has_perf_risk = comprehension.has_performance_impact or any(
            "perf" in r.lower() for r in comprehension.risk_areas
        )
        if has_perf_risk:
            selected.update(["performance", "bug", "test"])
            reasons.append("Performance risk flagged: activated Performance, Bug, and Test specialists.")

        # 3. Security-sensitive PR (auth, crypto, sensitive paths, or comprehension flag/risk_areas)
        sensitive_keywords = {"auth", "security", "crypto", "token", "password", "secret", "payment", "credential"}
        has_sensitive_paths = any(any(kw in f.lower() for kw in sensitive_keywords) for f in changed_files)
        has_sec_risk = (
            comprehension.has_security_impact
            or has_sensitive_paths
            or any("sec" in r.lower() or "auth" in r.lower() for r in comprehension.risk_areas)
        )

        if has_sec_risk:
            selected.update(["security", "bug"])
            reasons.append("Security risk or sensitive file paths identified: activated Security and Bug specialists.")

        # 4. Database or API contract changes
        has_db_api_risk = (
            comprehension.has_database_or_api_impact
            or any("api" in r.lower() or "contract" in r.lower() or "db" in r.lower() for r in comprehension.risk_areas)
            or any("api" in c.lower() for c in comprehension.changed_components)
        )
        if has_db_api_risk:
            selected.update(["security", "bug", "test"])
            reasons.append("Database / API schema or endpoint modification: activated Security, Bug, and Test specialists.")

        # 5. Default standard code change
        if not selected:
            selected.update(["security", "bug", "test"])
            reasons.append("Standard code PR: activated default suite (Security, Bug, Test specialists).")

        # Deterministic ordering
        execution_order = ["security", "bug", "test", "performance"]
        final_list = [agent for agent in execution_order if agent in selected]
        final_reason = " ".join(reasons)

        return final_list, final_reason
