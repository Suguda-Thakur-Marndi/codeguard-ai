"""Adversarial Judge for independent verification of candidate code review findings."""

import json
import time
from typing import Any

from app.agents.judge.confidence import ConfidencePolicy
from app.agents.judge.schemas import JudgeDecision, JudgeDecisionType
from app.agents.llm.provider import LLMProvider
from app.agents.prompts.registry import PromptRegistry
from app.agents.schemas.finding import ReviewFinding
from app.core.config import settings
from app.core.logging import TimingLogger, logger


class AdversarialJudge:
    """
    Independent adversarial judge evaluating candidate findings against 4 strict gates:
    Gate 1: Diff Boundary Conformity (Deterministic First)
    Gate 2: Contextual Factuality & Existing Guard Detection
    Gate 3: Actionability (Rejecting vague/cosmetic suggestions)
    Gate 4: Severity & Confidence Audit
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.model_tier = settings.JUDGE_MODEL_TIER
        self.max_retries = settings.JUDGE_MAX_RETRIES

    def evaluate_gate1_diff_boundary(
        self,
        finding: ReviewFinding,
        changed_files: list[str],
        valid_lines_by_file: dict[str, dict[str, list[int]]],
    ) -> tuple[bool, str | None]:
        """
        Gate 1: Diff Boundary Conformity (Deterministic validation).
        Must run BEFORE any LLM call to save tokens and latency.
        """
        # 1. File existence in PR diff
        if finding.file_path not in changed_files:
            return False, f"File '{finding.file_path}' is not part of this pull request."

        # 2. Line number check in changed hunk boundaries
        file_lines = valid_lines_by_file.get(finding.file_path, {})
        side_lines = file_lines.get(finding.side, [])

        if finding.line_number not in side_lines:
            return False, (
                f"Line {finding.line_number} ({finding.side}) does not belong to changed review lines "
                f"for '{finding.file_path}'. Allowed lines: {sorted(side_lines)[:10]}..."
            )

        # 3. Start line check if multi-line
        if finding.start_line is not None and finding.start_line > finding.line_number:
            return False, f"Multi-line start_line ({finding.start_line}) cannot exceed line_number ({finding.line_number})."

        return True, None

    async def evaluate_finding(
        self,
        finding: ReviewFinding,
        changed_files: list[str],
        valid_lines_by_file: dict[str, dict[str, list[int]]],
        diff_hunks: list[dict[str, Any]],
        source_and_ast_context: str,
        caller_and_guard_context: str,
        existing_tests_context: str,
    ) -> tuple[JudgeDecision, dict[str, Any]]:
        """
        Evaluate candidate finding through all 4 gates.
        Returns:
            (JudgeDecision, token_and_latency_metadata)
        """
        t0 = time.perf_counter()

        # ---------------------------------------------------------------------
        # GATE 1: Deterministic Diff Boundary Conformity
        # ---------------------------------------------------------------------
        boundary_ok, boundary_err = self.evaluate_gate1_diff_boundary(
            finding=finding,
            changed_files=changed_files,
            valid_lines_by_file=valid_lines_by_file,
        )

        if not boundary_ok:
            latency_ms = (time.perf_counter() - t0) * 1000.0
            logger.info(
                f"[Judge Gate 1 Reject] Finding '{finding.title}' on {finding.file_path}:{finding.line_number} "
                f"failed diff boundary conformity: {boundary_err}"
            )
            decision = JudgeDecision(
                finding_id=finding.finding_id,
                decision=JudgeDecisionType.REJECT,
                final_severity=finding.severity,
                judge_confidence=0.0,
                final_confidence=0.0,
                boundary_passed=False,
                factuality_passed=True,
                actionability_passed=True,
                severity_passed=True,
                rejection_reason="INVALID_DIFF_LOCATION",
                verification_summary=f"Gate 1 Rejection: {boundary_err}",
                evidence=[],
            )
            metadata = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
                "latency_ms": round(latency_ms, 2),
                "model_name": "deterministic_gate1",
            }
            return decision, metadata

        # ---------------------------------------------------------------------
        # GATES 2, 3, 4: Contextual Factuality, Actionability, Severity via LLM
        # ---------------------------------------------------------------------
        with TimingLogger("adversarial_judge_evaluation", {"finding_id": finding.finding_id}):
            system_prompt = PromptRegistry.get_system_prompt("judge.v1")

            reported_evidence_str = "\n".join(
                f"- [{ev.type}] {ev.file}:{ev.line_start or ''} - {ev.description}"
                for ev in finding.evidence
            ) or "No specific evidence items supplied."

            diff_lines_for_file = valid_lines_by_file.get(finding.file_path, {}).get(finding.side, [])
            user_prompt = PromptRegistry.format_user_prompt(
                agent_name="adversarial_judge",
                version="judge.v1",
                context_payload={
                    "agent_name": finding.agent_name,
                    "category": finding.category.value if hasattr(finding.category, "value") else str(finding.category),
                    "severity": finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity),
                    "file_path": finding.file_path,
                    "line_number": finding.line_number,
                    "side": finding.side,
                    "title": finding.title,
                    "description": finding.description,
                    "impact": finding.impact,
                    "recommendation": finding.recommendation,
                    "confidence": finding.confidence,
                    "reported_evidence": reported_evidence_str,
                    "valid_lines_by_file": f"{finding.file_path} [{finding.side}]: {diff_lines_for_file}",
                    "diff_hunks": json.dumps(diff_hunks, indent=2),
                    "source_and_ast_context": source_and_ast_context,
                    "caller_and_guard_context": caller_and_guard_context,
                    "existing_tests_context": existing_tests_context,
                },
            )

            # Generate structured response with up to max_retries
            response = None
            last_err = None
            for attempt in range(self.max_retries + 1):
                try:
                    response = await self.llm_provider.generate_structured(
                        prompt=user_prompt,
                        system_instruction=system_prompt,
                        response_schema=JudgeDecision,
                        model_tier=self.model_tier,
                    )
                    break
                except Exception as exc:
                    last_err = exc
                    if attempt == self.max_retries:
                        raise exc

            if response is None and last_err:
                raise last_err

            decision = response.data
            # Force finding_id consistency
            decision.finding_id = finding.finding_id

            # Compute transparent final confidence score using policy
            decision.final_confidence = ConfidencePolicy.calculate(
                specialist_confidence=finding.confidence,
                judge_confidence=decision.judge_confidence,
                decision=decision.decision,
                original_severity=finding.severity,
                final_severity=decision.final_severity,
                execution_passed=False,
            )

            # Check for vague recommendations deterministically if judge missed it
            if self._is_vague_recommendation(finding.recommendation):
                decision.actionability_passed = False
                if decision.decision == JudgeDecisionType.ACCEPT:
                    decision.decision = JudgeDecisionType.REJECT
                    decision.rejection_reason = "VAGUE_SUGGESTION"
                    decision.final_confidence = 0.0

            # Grounding evidence preservation
            if not decision.evidence:
                decision.evidence = finding.evidence

            latency_ms = (time.perf_counter() - t0) * 1000.0
            metadata = {
                "input_tokens": response.token_usage.input_tokens,
                "output_tokens": response.token_usage.output_tokens,
                "total_tokens": response.token_usage.total_tokens,
                "estimated_cost": response.token_usage.estimated_cost,
                "latency_ms": round(latency_ms, 2),
                "model_name": response.model_name,
            }

            return decision, metadata

    def _is_vague_recommendation(self, recommendation: str) -> bool:
        """Heuristic check to flag blatantly vague or generic suggestions."""
        vague_phrases = [
            "consider adding error handling",
            "consider adding tests",
            "follow best practices",
            "make sure this is safe",
            "refactor this method",
            "improve readability",
            "consider logging",
        ]
        rec_lower = recommendation.strip().lower()
        if len(rec_lower.split()) < 4:
            return True
        return any(vp in rec_lower for vp in vague_phrases) and len(rec_lower.split()) < 12
