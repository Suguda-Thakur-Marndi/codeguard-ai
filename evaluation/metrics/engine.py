"""Comprehensive empirical metrics engine for CodeGuard AI benchmark evaluations."""

import math
from dataclasses import asdict, dataclass, field
from typing import Any

from evaluation.metrics.definitions import (
    calculate_f1,
    calculate_precision,
    calculate_rate,
    calculate_recall,
)
from evaluation.validators.semantic_matcher import MatchResult


def percentile(data: list[float], pct: float) -> float:
    """Compute exact percentile value for a list of numbers."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(sorted_data[f], 2)
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return round(d0 + d1, 2)


@dataclass
class AgentMetricSummary:
    agent_name: str
    candidates_count: int = 0
    true_positives: int = 0
    false_positives: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    total_latency_ms: float = 0.0
    calls_count: int = 0
    failures_count: int = 0


@dataclass
class JudgeEffectivenessSummary:
    candidates_before_judge: int = 0
    findings_after_judge: int = 0
    true_positives_before_judge: int = 0
    false_positives_before_judge: int = 0
    true_positives_after_judge: int = 0
    false_positives_after_judge: int = 0
    noise_reduction_rate: float = 0.0
    tp_retention_rate: float = 0.0


@dataclass
class VerificationFunnelSummary:
    initial_candidates: int = 0
    gate1_diff_boundary_rejected: int = 0
    gate2_factuality_rejected: int = 0
    gate3_actionability_rejected: int = 0
    gate4_severity_downgraded: int = 0
    gate5_execution_rejected: int = 0
    deduplicated_count: int = 0
    final_publishable_count: int = 0


@dataclass
class BenchmarkMetricsSummary:
    """Overall aggregated metrics for a benchmark execution."""

    scenarios_total: int = 0
    scenarios_passed: int = 0
    scenarios_failed: int = 0

    # Core Detection Metrics
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0

    # Finding Counts
    total_predicted_findings: int = 0
    raw_candidates_total: int = 0
    final_findings_total: int = 0
    duplicate_count: int = 0
    duplicate_reduction_rate: float = 0.0

    # Line Accuracy
    valid_line_count: int = 0
    invalid_line_count: int = 0
    valid_line_rate: float = 0.0
    wrong_file_count: int = 0
    wrong_file_rate: float = 0.0
    wrong_line_count: int = 0
    wrong_line_rate: float = 0.0

    # Severity Accuracy
    exact_severity_count: int = 0
    exact_severity_rate: float = 0.0
    over_severity_count: int = 0
    over_severity_rate: float = 0.0
    under_severity_count: int = 0
    under_severity_rate: float = 0.0

    # Category Accuracy
    category_match_count: int = 0
    category_accuracy_rate: float = 0.0

    # Latency Percentiles (ms)
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0

    # AI Tokens & Estimated Cost
    input_tokens_total: int = 0
    output_tokens_total: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0

    # Failure Rates
    model_failure_count: int = 0
    system_failure_count: int = 0
    agent_failure_rate: float = 0.0
    mcp_tool_failure_rate: float = 0.0

    # Component Breakdowns
    agent_metrics: dict[str, AgentMetricSummary] = field(default_factory=dict)
    judge_effectiveness: JudgeEffectivenessSummary = field(default_factory=JudgeEffectivenessSummary)
    verification_funnel: VerificationFunnelSummary = field(default_factory=VerificationFunnelSummary)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics summary to a plain serializable dictionary."""
        d = asdict(self)
        return d


class MetricsEngine:
    """Engine for compiling empirical match results and runtime telemetry into official metrics."""

    @classmethod
    def compute_summary(
        cls,
        match_results: list[MatchResult],
        latencies_ms: list[float] | None = None,
        token_usage_records: list[dict[str, Any]] | None = None,
        agent_runs: list[dict[str, Any]] | None = None,
        verification_records: list[dict[str, Any]] | None = None,
        scenario_success_flags: list[bool] | None = None,
    ) -> BenchmarkMetricsSummary:
        """Calculate complete benchmark metrics from real execution outputs."""
        summary = BenchmarkMetricsSummary()
        summary.scenarios_total = len(match_results)

        if scenario_success_flags:
            summary.scenarios_passed = sum(1 for f in scenario_success_flags if f)
            summary.scenarios_failed = sum(1 for f in scenario_success_flags if not f)
        else:
            summary.scenarios_passed = len(match_results)

        # 1. Aggregate Match Results
        total_eval_findings = 0
        severity_eval_count = 0

        for m in match_results:
            summary.true_positives += len(m.true_positives)
            summary.false_positives += len(m.false_positives)
            summary.false_negatives += len(m.false_negatives)

            summary.total_predicted_findings += m.total_predicted
            summary.raw_candidates_total += m.raw_candidates_count
            summary.final_findings_total += m.final_findings_count
            summary.duplicate_count += m.duplicate_count

            summary.valid_line_count += m.valid_line_count
            summary.invalid_line_count += m.invalid_line_count
            summary.wrong_file_count += m.wrong_file_count
            summary.wrong_line_count += m.wrong_line_count

            summary.exact_severity_count += m.exact_severity_count
            summary.over_severity_count += m.over_severity_count
            summary.under_severity_count += m.under_severity_count
            severity_eval_count += (m.exact_severity_count + m.over_severity_count + m.under_severity_count)

            summary.category_match_count += m.category_matches
            total_eval_findings += len(m.true_positives)

        # 2. Precision, Recall, F1
        summary.precision = calculate_precision(summary.true_positives, summary.false_positives, summary.false_negatives)
        summary.recall = calculate_recall(summary.true_positives, summary.false_negatives)
        summary.f1 = calculate_f1(summary.precision, summary.recall)

        # 3. Accuracy Rates
        pred_lines_denom = summary.valid_line_count + summary.invalid_line_count
        summary.valid_line_rate = calculate_rate(summary.valid_line_count, pred_lines_denom, default=1.0)
        summary.wrong_file_rate = calculate_rate(summary.wrong_file_count, pred_lines_denom, default=0.0)
        summary.wrong_line_rate = calculate_rate(summary.wrong_line_count, pred_lines_denom, default=0.0)

        summary.exact_severity_rate = calculate_rate(summary.exact_severity_count, severity_eval_count, default=1.0)
        summary.over_severity_rate = calculate_rate(summary.over_severity_count, severity_eval_count, default=0.0)
        summary.under_severity_rate = calculate_rate(summary.under_severity_count, severity_eval_count, default=0.0)

        summary.category_accuracy_rate = calculate_rate(summary.category_match_count, total_eval_findings, default=1.0)

        if summary.raw_candidates_total > 0:
            summary.duplicate_reduction_rate = round(
                float(summary.duplicate_count) / float(summary.raw_candidates_total), 4
            )

        # 4. Latency Percentiles
        l_list = latencies_ms or []
        if l_list:
            summary.avg_latency_ms = round(sum(l_list) / len(l_list), 2)
            summary.p50_latency_ms = percentile(l_list, 50.0)
            summary.p95_latency_ms = percentile(l_list, 95.0)
            summary.p99_latency_ms = percentile(l_list, 99.0)

        # 5. Token & Cost Accounting
        if token_usage_records:
            for rec in token_usage_records:
                summary.input_tokens_total += rec.get("input_tokens", 0)
                summary.output_tokens_total += rec.get("output_tokens", 0)
                summary.total_tokens += rec.get("total_tokens", 0)
                summary.estimated_cost_usd += rec.get("estimated_cost", 0.0)
        summary.estimated_cost_usd = round(summary.estimated_cost_usd, 6)

        # 6. Per-Agent Telemetry
        if agent_runs:
            for ar in agent_runs:
                name = ar.get("agent_name", "unknown")
                if name not in summary.agent_metrics:
                    summary.agent_metrics[name] = AgentMetricSummary(agent_name=name)
                am = summary.agent_metrics[name]
                am.calls_count += 1
                am.total_tokens += ar.get("total_tokens", 0)
                am.estimated_cost += ar.get("estimated_cost", 0.0)
                am.total_latency_ms += ar.get("latency_ms", 0.0)
                am.candidates_count += ar.get("candidates_count", 0)
                if ar.get("status") == "FAILED":
                    am.failures_count += 1

        # 7. Judge & Verification Telemetry
        if verification_records:
            funnel = summary.verification_funnel
            judge = summary.judge_effectiveness
            for vr in verification_records:
                funnel.initial_candidates += vr.get("initial_candidates", 0)
                funnel.gate1_diff_boundary_rejected += vr.get("gate1_rejected", 0)
                funnel.gate2_factuality_rejected += vr.get("gate2_rejected", 0)
                funnel.gate3_actionability_rejected += vr.get("gate3_rejected", 0)
                funnel.gate4_severity_downgraded += vr.get("gate4_downgraded", 0)
                funnel.gate5_execution_rejected += vr.get("gate5_rejected", 0)
                funnel.deduplicated_count += vr.get("deduplicated_count", 0)
                funnel.final_publishable_count += vr.get("final_publishable_count", 0)

                judge.candidates_before_judge += vr.get("candidates_before_judge", 0)
                judge.findings_after_judge += vr.get("findings_after_judge", 0)
                judge.true_positives_before_judge += vr.get("tp_before_judge", 0)
                judge.false_positives_before_judge += vr.get("fp_before_judge", 0)
                judge.true_positives_after_judge += vr.get("tp_after_judge", 0)
                judge.false_positives_after_judge += vr.get("fp_after_judge", 0)

            if judge.false_positives_before_judge > 0:
                reduced_fp = judge.false_positives_before_judge - judge.false_positives_after_judge
                judge.noise_reduction_rate = round(float(reduced_fp) / float(judge.false_positives_before_judge), 4)
            if judge.true_positives_before_judge > 0:
                judge.tp_retention_rate = round(
                    float(judge.true_positives_after_judge) / float(judge.true_positives_before_judge), 4
                )

        return summary
