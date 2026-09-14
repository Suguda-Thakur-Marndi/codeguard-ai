"""Deterministic confidence calculation policy combining specialist and judge assessments."""

from app.agents.judge.schemas import JudgeDecisionType
from app.agents.schemas.finding import FindingSeverity


class ConfidencePolicy:
    """
    Transparent deterministic policy for computing final finding confidence.

    Policy Rules:
    1. Rejection Rule: If judge decision is REJECT, final_confidence is set to 0.0.
    2. Weighted Confirmation:
       - Specialist confidence has 35% weight.
       - Judge confidence has 65% weight (higher weight due to full context re-reading and existing guard inspection).
       base_confidence = 0.35 * specialist_conf + 0.65 * judge_conf
    3. Execution Confirmation Bonus:
       - If execution validation passes, add +0.05 bonus.
    4. Severity Downgrade Penalty:
       - If the judge downgraded severity from specialist assignment, deduct 0.05.
    5. Bounds:
       - Bounded strictly between 0.0 and 0.99.
    """

    @staticmethod
    def calculate(
        specialist_confidence: float,
        judge_confidence: float,
        decision: JudgeDecisionType,
        original_severity: FindingSeverity | str | None = None,
        final_severity: FindingSeverity | str | None = None,
        execution_passed: bool = False,
    ) -> float:
        if decision == JudgeDecisionType.REJECT:
            return 0.0

        # Base weighted confidence
        spec_c = max(0.0, min(1.0, float(specialist_confidence)))
        judge_c = max(0.0, min(1.0, float(judge_confidence)))
        conf = (0.35 * spec_c) + (0.65 * judge_c)

        # Execution validation bonus
        if execution_passed:
            conf += 0.05

        # Severity downgrade penalty
        if original_severity and final_severity:
            orig_str = original_severity.value if hasattr(original_severity, "value") else str(original_severity)
            fin_str = final_severity.value if hasattr(final_severity, "value") else str(final_severity)
            if orig_str != fin_str and orig_str in ("CRITICAL", "HIGH") and fin_str not in ("CRITICAL", "HIGH"):
                conf -= 0.05

        return round(max(0.1, min(0.99, conf)), 2)

    @staticmethod
    def describe_policy() -> str:
        return (
            "Deterministic Policy: 35% specialist confidence + 65% judge confidence. "
            "+0.05 bonus if execution validated. -0.05 penalty if severity downgraded. "
            "0.0 if rejected. Bounded in [0.10, 0.99]."
        )
