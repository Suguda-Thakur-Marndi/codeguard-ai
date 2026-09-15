"""Batch runner executing benchmark suites with bounded concurrency."""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

from evaluation.metrics.engine import BenchmarkMetricsSummary, MetricsEngine
from evaluation.runners.pipeline_runner import PipelineRunner, ScenarioExecutionResult
from evaluation.scenarios.schema import BenchmarkScenario


@dataclass
class BatchResult:
    """Consolidated outcome of running a batch of benchmark scenarios."""

    run_id: str
    run_name: str
    dataset_version: str
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    concurrency: int
    summary_metrics: BenchmarkMetricsSummary
    scenario_results: list[ScenarioExecutionResult] = field(default_factory=list)
    failure_reasons: dict[str, str] = field(default_factory=dict)


class BatchBenchmarkRunner:
    """Executes full benchmark test suites with bounded concurrency and failure isolation."""

    def __init__(
        self,
        runner: PipelineRunner | None = None,
        max_concurrency: int = 1,
    ):
        self.runner = runner or PipelineRunner()
        self.max_concurrency = max_concurrency

    async def run_batch(
        self,
        scenarios: list[BenchmarkScenario],
        run_name: str = "benchmark-suite-run",
        dataset_version: str = "v1",
    ) -> BatchResult:
        """Run all provided scenarios with concurrency bounds."""
        run_id = f"run-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
        started_at = datetime.now(UTC)
        t0 = time.perf_counter()

        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _execute_with_sem(scenario: BenchmarkScenario) -> ScenarioExecutionResult:
            async with semaphore:
                return await self.runner.run_scenario(scenario)

        tasks = [_execute_with_sem(sc) for sc in scenarios]
        scenario_results: list[ScenarioExecutionResult] = await asyncio.gather(*tasks)

        t_end = time.perf_counter()
        completed_at = datetime.now(UTC)
        duration_sec = round(t_end - t0, 2)

        match_results = []
        latencies = []
        tokens = []
        agent_runs = []
        verification_records = []
        failures = {}

        for r in scenario_results:
            latencies.append(r.latency_ms)
            if r.status == "COMPLETED" and r.match_result:
                match_results.append(r.match_result)
            else:
                failures[r.scenario_id] = r.error_message or "Unknown failure"

            tokens.append(
                {
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "total_tokens": r.total_tokens,
                    "estimated_cost": r.estimated_cost,
                }
            )
            agent_runs.extend(r.agent_runs)
            if r.verification_record:
                verification_records.append(r.verification_record)

        summary = MetricsEngine.compute_summary(
            match_results=match_results,
            latencies_ms=latencies,
            token_usage_records=tokens,
            agent_runs=agent_runs,
            verification_records=verification_records,
            scenario_success_flags=[r.status == "COMPLETED" for r in scenario_results],
        )

        return BatchResult(
            run_id=run_id,
            run_name=run_name,
            dataset_version=dataset_version,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_sec,
            concurrency=self.max_concurrency,
            summary_metrics=summary,
            scenario_results=scenario_results,
            failure_reasons=failures,
        )
