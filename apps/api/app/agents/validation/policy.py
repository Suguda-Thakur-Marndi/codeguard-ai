"""Validation policy engine determining execution and analysis strategy for findings."""

import enum

from app.agents.schemas.finding import FindingCategory, FindingSeverity, ReviewFinding


class ExecutionDecision(enum.StrEnum):
    EXECUTE = "EXECUTE"
    STATIC_ONLY = "STATIC_ONLY"
    NO_EXECUTION = "NO_EXECUTION"


class ValidationPolicy:
    """
    Deterministic policy engine that decides whether a candidate finding requires:
    - EXECUTE: Behavioral runtime execution in isolated Docker sandbox
    - STATIC_ONLY: Deterministic static analysis (Ruff, ESLint, Semgrep, AST inspection)
    - NO_EXECUTION: Static reasoning only (e.g. style, documentation, pure advisory)
    """

    @classmethod
    def evaluate(
        cls,
        category: FindingCategory | str,
        severity: FindingSeverity | str,
        confidence: float,
        has_test_suite: bool = True,
        is_safe_sandbox_target: bool = True,
    ) -> ExecutionDecision:
        cat_str = category.value if hasattr(category, "value") else str(category)
        sev_str = severity.value if hasattr(severity, "value") else str(severity)

        # 1. Pure advisory / low-severity non-functional issues
        if sev_str == "ADVISORY":
            return ExecutionDecision.NO_EXECUTION

        # 2. Runtime functional defects (BUG, ERROR_HANDLING)
        if cat_str in ("BUG", "ERROR_HANDLING"):
            if has_test_suite and is_safe_sandbox_target and confidence >= 0.7:
                return ExecutionDecision.EXECUTE
            return ExecutionDecision.STATIC_ONLY

        # 3. Contract & test coverage issues
        if cat_str in ("TEST_COVERAGE", "CONTRACT"):
            return ExecutionDecision.STATIC_ONLY

        # 4. Security findings
        if cat_str == "SECURITY":
            # Execution only when safe sandbox target is confirmed and high severity
            if sev_str in ("CRITICAL", "HIGH") and is_safe_sandbox_target and has_test_suite:
                return ExecutionDecision.EXECUTE
            return ExecutionDecision.STATIC_ONLY

        # 5. Performance findings
        if cat_str == "PERFORMANCE":
            if has_test_suite and is_safe_sandbox_target and sev_str in ("CRITICAL", "HIGH"):
                return ExecutionDecision.EXECUTE
            return ExecutionDecision.STATIC_ONLY

        # Default fallback
        return ExecutionDecision.NO_EXECUTION

    @classmethod
    def evaluate_finding(
        cls,
        finding: ReviewFinding,
        has_test_suite: bool = True,
        is_safe_sandbox_target: bool = True,
    ) -> ExecutionDecision:
        return cls.evaluate(
            category=finding.category,
            severity=finding.severity,
            confidence=finding.confidence,
            has_test_suite=has_test_suite,
            is_safe_sandbox_target=is_safe_sandbox_target,
        )
