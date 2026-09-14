"""Bug & Error Handling Specialist Agent: detects functional defects and runtime errors."""

from typing import Any

from app.agents.llm.provider import LLMProvider, ModelTier
from app.agents.prompts.registry import PromptRegistry
from app.agents.schemas.finding import SpecialistFindingsOutput
from app.agents.specialists.base import BaseSpecialistAgent
from app.core.config import settings


class BugAgent(BaseSpecialistAgent):
    """Bug & error handling specialist identifying functional defects, null handling, and state regressions."""

    def __init__(self, provider: LLMProvider):
        tier = (
            ModelTier.FAST
            if settings.MODEL_TIER_BUG == "fast"
            else ModelTier.REASONING
        )
        super().__init__(
            agent_name="bug",
            prompt_version="bug.v1",
            provider=provider,
            model_tier=tier,
            version="1.0.0",
        )

    async def run(
        self,
        changed_lines_by_file: dict[str, dict[str, list[int]]],
        diff_hunks_by_file: dict[str, list[dict[str, Any]]],
        ast_chunks_by_file: dict[str, list[dict[str, Any]]],
        source_code_by_file: dict[str, str],
        context_by_symbol: dict[str, dict[str, Any]],
    ) -> tuple[SpecialistFindingsOutput, dict[str, Any]]:
        """Run Bug Specialist Agent and return candidate findings."""
        prompt_tmpl = PromptRegistry.get(self.prompt_version)

        valid_lines_str = self._format_valid_lines(changed_lines_by_file)

        hunk_lines = []
        for file_path, hunks in diff_hunks_by_file.items():
            hunk_lines.append(f"--- File: {file_path} ---")
            for h in hunks:
                hunk_lines.append(f"@@ -{h.get('old_start')},{h.get('old_lines')} +{h.get('new_start')},{h.get('new_lines')} @@")
                for line in h.get("lines", []):
                    line_type = line.get("line_type", "context")
                    prefix = "+" if line_type == "added" else ("-" if line_type == "deleted" else " ")
                    hunk_lines.append(f"{prefix} {line.get('content', '')}")
        diff_hunks_str = "\n".join(hunk_lines) if hunk_lines else "No diff hunks."

        source_ast_lines = []
        for file_path, chunks in ast_chunks_by_file.items():
            source_ast_lines.append(f"=== File AST Chunks: {file_path} ===")
            for ch in chunks[:6]:
                sym = ch.get("symbol_name") or "unnamed"
                span = f"L{ch.get('start_line')}-L{ch.get('end_line')}"
                code_snippet = ch.get("code_snippet", "")[:1200]
                source_ast_lines.append(f"Entity: `{sym}` ({ch.get('node_type')}) [{span}]:\n```\n{code_snippet}\n```")
        source_ast_str = "\n".join(source_ast_lines) if source_ast_lines else "No AST chunks."

        dep_context_lines = []
        for sym, ctx in list(context_by_symbol.items())[:8]:
            callers = ctx.get("direct_callers", [])
            deps = ctx.get("direct_dependencies", [])
            dep_context_lines.append(f"Symbol `{sym}`:")
            if callers:
                dep_context_lines.append(f"  Callers: {callers[:4]}")
            if deps:
                dep_context_lines.append(f"  Dependencies: {deps[:4]}")
        dep_context_str = "\n".join(dep_context_lines) if dep_context_lines else "No dependency context."

        user_prompt = prompt_tmpl.user_prompt_template.format(
            valid_lines_by_file=valid_lines_str,
            diff_hunks=self._truncate_context_budget(diff_hunks_str, 5000),
            source_and_ast_context=self._truncate_context_budget(source_ast_str, 6000),
            dependency_context=self._truncate_context_budget(dep_context_str, 3000),
        )

        output, run_meta = await self.execute_structured_with_retry(
            user_prompt=user_prompt,
            response_schema=SpecialistFindingsOutput,
        )

        for f in output.findings:
            f.agent_name = self.agent_name

        return output, run_meta
