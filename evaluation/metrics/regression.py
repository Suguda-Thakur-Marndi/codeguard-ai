"""Regression detection between benchmark runs."""

from dataclasses import dataclass
from typing import Any

from evaluation.metrics.engine import BenchmarkMetricsSummary


@dataclass
class RegressionComparison:
    """Detailed delta report comparing baseline vs candidate benchmark runs."""

    baseline_run_id: str
    candidate_run_id: str
    is_regression: bool
    reasons: list[str]

    # Core Metric Deltas (candidate - baseline)
    delta_precision: float
    delta_recall: float
    delta_f1: float
    delta_valid_line_rate: float
    delta_severity_accuracy: float
    delta_category_accuracy: float

    # Performance & Cost Deltas
    delta_avg_latency_ms: float
    delta_p95_latency_ms: float
    delta_estimated_cost_usd: float

    baseline_metrics: dict[str, Any]
    candidate_metrics: dict[str, Any]


class RegressionDetector:
    """Compares candidate run to baseline and flags quality or performance regressions."""

    def __init__(
        self,
        f1_tolerance: float = 0.05,
        precision_tolerance: float = 0.05,
        recall_tolerance: float = 0.05,
        latency_increase_ratio_tolerance: float = 0.25,
        min_sample_size: int = 3,
    ):
        self.f1_tolerance = f1_tolerance
        self.precision_tolerance = precision_tolerance
        self.recall_tolerance = recall_tolerance
        self.latency_increase_ratio_tolerance = latency_increase_ratio_tolerance
        self.min_sample_size = min_sample_size

    def compare(
        self,
        baseline_run_id: str,
        baseline: BenchmarkMetricsSummary,
        candidate_run_id: str,
        candidate: BenchmarkMetricsSummary,
    ) -> RegressionComparison:
        """Compare candidate against baseline metrics."""
        delta_p = round(candidate.precision - baseline.precision, 4)
        delta_r = round(candidate.recall - baseline.recall, 4)
        delta_f1 = round(candidate.f1 - baseline.f1, 4)
        delta_line = round(candidate.valid_line_rate - baseline.valid_line_rate, 4)
        delta_sev = round(candidate.exact_severity_rate - baseline.exact_severity_rate, 4)
        delta_cat = round(candidate.category_accuracy_rate - baseline.category_accuracy_rate, 4)
        delta_lat = round(candidate.avg_latency_ms - baseline.avg_latency_ms, 2)
        delta_p95 = round(candidate.p95_latency_ms - baseline.p95_latency_ms, 2)
        delta_cost = round(candidate.estimated_cost_usd - baseline.estimated_cost_usd, 6)

        reasons: list[str] = []
        is_regression = False

        # Only flag statistical regressions if sample size is sufficient
        if candidate.scenarios_total >= self.min_sample_size and baseline.scenarios_total >= self.min_sample_size:
            if delta_f1 < -self.f1_tolerance:
                is_regression = True
                reasons.append(
                    f"F1 score regressed by {abs(delta_f1):.4f} (from {baseline.f1:.4f} to {candidate.f1:.4f})"
                )

            if delta_p < -self.precision_tolerance:
                is_regression = True
                reasons.append(
                    f"Precision regressed by {abs(delta_p):.4f} (from {baseline.precision:.4f} to {candidate.precision:.4f})"
                )

            if delta_r < -self.recall_tolerance:
                is_regression = True
                reasons.append(
                    f"Recall regressed by {abs(delta_r):.4f} (from {baseline.recall:.4f} to {candidate.recall:.4f})"
                )

            if baseline.avg_latency_ms > 0:
                latency_ratio = delta_lat / baseline.avg_latency_ms
                if latency_ratio > self.latency_increase_ratio_tolerance and delta_lat > 500.0:
                    reasons.append(
                        f"Average latency increased by {latency_ratio * 100:.1f}% (+{delta_lat:.1f}ms)"
                    )

        return RegressionComparison(
            baseline_run_id=baseline_run_id,
            candidate_run_id=candidate_run_id,
            is_regression=is_regression,
            reasons=reasons,
            delta_precision=delta_p,
            delta_recall=delta_r,
            delta_f1=delta_f1,
            delta_valid_line_rate=delta_line,
            delta_severity_accuracy=delta_sev,
            delta_category_accuracy=delta_cat,
            delta_avg_latency_ms=delta_lat,
            delta_p95_latency_ms=delta_p95,
            delta_estimated_cost_usd=delta_cost,
            baseline_metrics=baseline.to_dict(),
            candidate_metrics=candidate.to_dict(),
        )
