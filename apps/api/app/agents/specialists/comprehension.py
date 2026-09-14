"""Comprehension Agent: analyzes PR intent, functional changes, and architectural risk areas."""

from typing import Any

from app.agents.llm.provider import LLMProvider, ModelTier
from app.agents.prompts.registry import PromptRegistry
from app.agents.schemas.comprehension import ComprehensionResult
from app.agents.specialists.base import BaseSpecialistAgent
from app.core.config import settings


class ComprehensionAgent(BaseSpecialistAgent):
    """Comprehension Agent understanding what the PR changes and identifying risk domains."""

    def __init__(self, provider: LLMProvider):
        tier = (
            ModelTier.FAST
            if settings.MODEL_TIER_COMPREHENSION == "fast"
            else ModelTier.REASONING
        )
        super().__init__(
            agent_name="comprehension",
            prompt_version="comprehension.v1",
            provider=provider,
            model_tier=tier,
            version="1.0.0",
        )

    async def run(
        self,
        title: str,
        description: str,
        base_sha: str,
        head_sha: str,
        diff_hunks_by_file: dict[str, list[dict[str, Any]]],
        ast_chunks_by_file: dict[str, list[dict[str, Any]]],
        context_by_symbol: dict[str, dict[str, Any]],
    ) -> tuple[ComprehensionResult, dict[str, Any]]:
        """Run Comprehension Agent and return ComprehensionResult with execution metadata."""
        prompt_tmpl = PromptRegistry.get(self.prompt_version)

        # 1. Format diff summary
        diff_summary_lines = []
        for f, hunks in diff_hunks_by_file.items():
            diff_summary_lines.append(f"File: {f} ({len(hunks)} changed hunks)")
            for h in hunks[:3]:
                header = h.get("section_header", "")
                diff_summary_lines.append(f"  @@ L{h.get('new_start')},+{h.get('new_lines')} @@ {header}")
        diff_summary_str = "\n".join(diff_summary_lines) if diff_summary_lines else "No diff hunks."

        # 2. Format AST context
        ast_lines = []
        for f, chunks in ast_chunks_by_file.items():
            for ch in chunks[:5]:
                sym = ch.get("symbol_name") or ch.get("entity_name") or "unnamed"
                parent = ch.get("parent_symbol")
                node_type = ch.get("node_type")
                span = f"L{ch.get('start_line')}-L{ch.get('end_line')}"
                ast_lines.append(f"- [{node_type}] {sym} (Parent: {parent}) {span} in {f}")
        ast_context_str = "\n".join(ast_lines) if ast_lines else "No AST chunks found."

        # 3. Format Callers and Dependencies
        caller_dep_lines = []
        for sym, ctx in list(context_by_symbol.items())[:10]:
            callers = ctx.get("direct_callers", [])
            deps = ctx.get("direct_dependencies", [])
            caller_dep_lines.append(f"Symbol `{sym}`:")
            if callers:
                caller_dep_lines.append(f"  Direct callers: {callers[:5]}")
            if deps:
                caller_dep_lines.append(f"  Dependencies: {deps[:5]}")
        caller_dep_str = "\n".join(caller_dep_lines) if caller_dep_lines else "None recorded."

        # Build prompt and apply budget
        user_prompt = prompt_tmpl.user_prompt_template.format(
            title=title or "Untitled PR",
            description=description or "No description provided.",
            base_sha=base_sha,
            head_sha=head_sha,
            diff_summary=self._truncate_context_budget(diff_summary_str, 4000),
            ast_context=self._truncate_context_budget(ast_context_str, 4000),
            caller_dependency_context=self._truncate_context_budget(caller_dep_str, 4000),
        )

        return await self.execute_structured_with_retry(
            user_prompt=user_prompt,
            response_schema=ComprehensionResult,
        )
