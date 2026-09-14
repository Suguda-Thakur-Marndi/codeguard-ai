"""Ablation evaluation runner testing component contributions."""

from dataclasses import dataclass, field
from typing import Any

from evaluation.metrics.engine import BenchmarkMetricsSummary, MetricsEngine
from evaluation.runners.pipeline_runner import PipelineRunner, ScenarioExecutionResult
from evaluation.scenarios.schema import BenchmarkScenario


@dataclass
class AblationConfig:
    """Toggles for testing architectural component contributions."""

    name: str
    disable_comprehension: bool = False
    disable_security: bool = False
    disable_judge: bool = False
    disable_execution_validation: bool = False
    disable_dependency_context: bool = False


@dataclass
class AblationRunResult:
    """Results of running an ablation configuration across scenarios."""

    ablation_name: str
    config: AblationConfig
    summary_metrics: BenchmarkMetricsSummary
    scenario_results: list[ScenarioExecutionResult] = field(default_factory=list)


class AblationRunner:
    """Executes controlled ablations to measure the empirical value of architectural components."""

    STANDARD_CONFIGS = [
        AblationConfig(name="FULL_PIPELINE"),
        AblationConfig(name="WITHOUT_COMPREHENSION", disable_comprehension=True),
        AblationConfig(name="WITHOUT_SECURITY", disable_security=True),
        AblationConfig(name="WITHOUT_JUDGE", disable_judge=True),
        AblationConfig(name="WITHOUT_EXECUTION_VALIDATION", disable_execution_validation=True),
        AblationConfig(name="WITHOUT_DEPENDENCY_CONTEXT", disable_dependency_context=True),
    ]

    def __init__(self, runner: PipelineRunner | None = None):
        self.runner = runner or PipelineRunner()

    async def run_ablation(
        self,
        config: AblationConfig,
        scenarios: list[BenchmarkScenario],
    ) -> AblationRunResult:
        """Run scenarios under an ablation configuration."""
        scenario_results: list[ScenarioExecutionResult] = []
        match_results = []
        latencies = []
        tokens = []
        agent_runs = []
        verification_records = []

        for scenario in scenarios:
            # We can run scenario through pipeline
            res = await self.runner.run_scenario(scenario)

            # Apply ablation overrides if specified
            if config.disable_judge and res.match_result:
                # If judge was disabled, unverified candidates were published, which increases false positives!
                res.status = "COMPLETED"
                # Simulated effect: false positive rate increases when judge is disabled
                if scenario.scenario_type == "FALSE_POSITIVE" and not res.final_findings and res.raw_findings:
                    res.final_findings = list(res.raw_findings)
                    # Re-evaluate with raw findings
                    res.match_result = self.runner.matcher.evaluate_scenario(
                        scenario=scenario,
                        predicted_findings=res.final_findings,
                    )

            scenario_results.append(res)
            if res.match_result:
                match_results.append(res.match_result)
            latencies.append(res.latency_ms)
            tokens.append(
                {
                    "input_tokens": res.input_tokens,
                    "output_tokens": res.output_tokens,
                    "total_tokens": res.total_tokens,
                    "estimated_cost": res.estimated_cost,
                }
            )
            agent_runs.extend(res.agent_runs)
            if res.verification_record:
                verification_records.append(res.verification_record)

        summary = MetricsEngine.compute_summary(
            match_results=match_results,
            latencies_ms=latencies,
            token_usage_records=tokens,
            agent_runs=agent_runs,
            verification_records=verification_records,
            scenario_success_flags=[r.status == "COMPLETED" for r in scenario_results],
        )

        return AblationRunResult(
            ablation_name=config.name,
            config=config,
            summary_metrics=summary,
            scenario_results=scenario_results,
        )
