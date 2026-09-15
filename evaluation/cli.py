"""Command Line Interface for CodeGuard AI Empirical Benchmark Suite."""

import argparse
import asyncio
import json
import os
import sys

from evaluation.metrics.engine import BenchmarkMetricsSummary
from evaluation.metrics.regression import RegressionDetector
from evaluation.reports.generator import BenchmarkReportGenerator
from evaluation.runners.ablation_runner import AblationRunner
from evaluation.runners.batch_runner import BatchBenchmarkRunner
from evaluation.runners.pipeline_runner import PipelineRunner
from evaluation.scenarios.loader import ScenarioLoader


def cmd_list(args: argparse.Namespace) -> int:
    """List available benchmark datasets, categories, and scenarios."""
    loader = ScenarioLoader()
    datasets = loader.list_datasets()
    print("=" * 70)
    print("CODEGUARD AI BENCHMARK CATALOG")
    print("=" * 70)
    print(f"Available Datasets: {datasets}")

    version = args.dataset or "v1"
    scenarios = loader.load_scenarios(version=version, category=args.category, language=args.language)
    print(f"\nScenarios in dataset '{version}' ({len(scenarios)} matching):")
    print("-" * 70)
    for sc in scenarios:
        print(f"  [{sc.scenario_id}] {sc.name}")
        print(f"      Category: {sc.category} | Lang: {sc.language} | Type: {sc.scenario_type} | Diff: {sc.difficulty}")
        print(f"      Ground Truth Findings: {len(sc.ground_truth_findings)} | Target: {sc.repository_fixture}")
    print("=" * 70)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate scenario schemas and ground-truth definitions."""
    loader = ScenarioLoader()
    version = args.dataset or "v1"
    print(f"Validating dataset '{version}' schemas and ground-truth definitions...")
    try:
        ds = loader.load_dataset(version)
        print(f"[OK] Successfully validated {len(ds.scenarios)} scenarios against Pydantic schema.")
        for sc in ds.scenarios:
            assert sc.scenario_id, "Missing scenario_id"
            assert sc.diff, "Missing diff"
            if sc.ground_truth_findings:
                for gt in sc.ground_truth_findings:
                    assert gt.file_path, f"{sc.scenario_id}: ground truth missing file_path"
                    assert gt.line_start > 0, f"{sc.scenario_id}: line_start must be positive"
        print(f"[PASS] All {len(ds.scenarios)} scenarios in dataset '{version}' passed integrity validation.")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Scenario validation failed: {exc}", file=sys.stderr)
        return 1


def cmd_run(args: argparse.Namespace) -> int:
    """Execute benchmark run across scenarios."""
    loader = ScenarioLoader()
    version = args.dataset or "v1"

    scenarios = loader.load_scenarios(
        version=version,
        scenario_id=args.scenario,
        category=args.category,
        language=args.language,
    )

    if not scenarios:
        print(f"No scenarios found matching filters: scenario={args.scenario}, category={args.category}, language={args.language}")
        return 1

    print("=" * 75)
    print(f"EXECUTING CODEGUARD AI BENCHMARK RUN: {len(scenarios)} SCENARIO(S)")
    print(f"Dataset: {version} | Concurrency: {args.concurrency}")
    print("=" * 75)

    pipeline_runner = PipelineRunner()

    if args.ablation:
        print(f"Running Ablation Mode: {args.ablation}")
        config = next((cfg for cfg in AblationRunner.STANDARD_CONFIGS if cfg.name == args.ablation), None)
        if not config:
            print(f"Unknown ablation '{args.ablation}'. Choose from: {[c.name for c in AblationRunner.STANDARD_CONFIGS]}")
            return 1
        ablation_runner = AblationRunner(pipeline_runner)
        res = asyncio.run(ablation_runner.run_ablation(config, scenarios))
        print("\nAblation Metrics Summary:")
        m = res.summary_metrics
        print(f"  Precision: {m.precision * 100:.1f}% | Recall: {m.recall * 100:.1f}% | F1: {m.f1:.4f}")
        return 0

    batch_runner = BatchBenchmarkRunner(pipeline_runner, max_concurrency=args.concurrency)
    result = asyncio.run(
        batch_runner.run_batch(
            scenarios=scenarios,
            run_name=args.name or "cli-benchmark-run",
            dataset_version=version,
        )
    )

    md_report = BenchmarkReportGenerator.generate_markdown(result)
    print("\n" + md_report)

    # Export options
    if args.export_md:
        with open(args.export_md, "w", encoding="utf-8") as f:
            f.write(md_report)
        print(f"Exported Markdown report to: {args.export_md}")

    if args.export_json:
        with open(args.export_json, "w", encoding="utf-8") as f:
            f.write(BenchmarkReportGenerator.generate_json(result))
        print(f"Exported JSON report to: {args.export_json}")

    if args.export_csv:
        with open(args.export_csv, "w", encoding="utf-8") as f:
            f.write(BenchmarkReportGenerator.generate_csv(result))
        print(f"Exported CSV report to: {args.export_csv}")

    return 0 if result.summary_metrics.scenarios_failed == 0 else 1


def cmd_regression(args: argparse.Namespace) -> int:
    """Compare candidate benchmark run against baseline run to detect regressions."""
    baseline_path = args.baseline or "benchmark_report.json"
    if not os.path.exists(baseline_path):
        print(f"Error: Baseline report '{baseline_path}' not found.", file=sys.stderr)
        return 1

    with open(baseline_path, encoding="utf-8") as f:
        baseline_raw = json.load(f)

    baseline_metrics_dict = baseline_raw.get("metrics", {})
    baseline_summary = BenchmarkMetricsSummary(
        **{k: v for k, v in baseline_metrics_dict.items() if k in BenchmarkMetricsSummary.__dataclass_fields__}
    )

    if args.candidate:
        if not os.path.exists(args.candidate):
            print(f"Error: Candidate report '{args.candidate}' not found.", file=sys.stderr)
            return 1
        with open(args.candidate, encoding="utf-8") as f:
            candidate_raw = json.load(f)
        candidate_summary = BenchmarkMetricsSummary(
            **{k: v for k, v in candidate_raw.get("metrics", {}).items() if k in BenchmarkMetricsSummary.__dataclass_fields__}
        )
        candidate_id = candidate_raw.get("run_id", "candidate-run")
    else:
        # Run scenarios to generate fresh candidate
        loader = ScenarioLoader()
        version = args.dataset or "v1"
        scenarios = loader.load_scenarios(version=version)
        pipeline_runner = PipelineRunner()
        batch_runner = BatchBenchmarkRunner(pipeline_runner, max_concurrency=args.concurrency)
        res = asyncio.run(
            batch_runner.run_batch(
                scenarios=scenarios,
                run_name="regression-check",
                dataset_version=version,
            )
        )
        candidate_summary = res.summary_metrics
        candidate_id = res.run_id

    detector = RegressionDetector(
        f1_tolerance=args.f1_tolerance,
        precision_tolerance=args.precision_tolerance,
        recall_tolerance=args.recall_tolerance,
    )
    comp = detector.compare(
        baseline_run_id=baseline_raw.get("run_id", "baseline"),
        baseline=baseline_summary,
        candidate_run_id=candidate_id,
        candidate=candidate_summary,
    )

    print("=" * 70)
    print("CODEGUARD AI BENCHMARK REGRESSION ANALYSIS")
    print("=" * 70)
    print(f"Baseline Run:  {comp.baseline_run_id} (F1: {baseline_summary.f1:.4f}, P: {baseline_summary.precision * 100:.1f}%, R: {baseline_summary.recall * 100:.1f}%)")
    print(f"Candidate Run: {comp.candidate_run_id} (F1: {candidate_summary.f1:.4f}, P: {candidate_summary.precision * 100:.1f}%, R: {candidate_summary.recall * 100:.1f}%)")
    print(f"Delta F1:        {comp.delta_f1:+.4f}")
    print(f"Delta Precision: {comp.delta_precision:+.4f}")
    print(f"Delta Recall:    {comp.delta_recall:+.4f}")
    print(f"Delta Latency:   {comp.delta_avg_latency_ms:+.2f} ms")
    print(f"Delta Cost:      ${comp.delta_estimated_cost_usd:+.6f}")
    print("-" * 70)
    if comp.is_regression:
        print("[REGRESSION DETECTED]")
        for reason in comp.reasons:
            print(f"  - {reason}")
        print("=" * 70)
        return 1

    print("[PASS] Zero performance or quality regressions detected!")
    print("=" * 70)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="benchmark",
        description="CodeGuard AI Phase 7 Empirical Evaluation & Benchmarking CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List scenarios and datasets")
    p_list.add_argument("--dataset", "-d", default="v1", help="Dataset version (default: v1)")
    p_list.add_argument("--category", "-c", help="Filter by category")
    p_list.add_argument("--language", "-l", help="Filter by language")
    p_list.set_defaults(func=cmd_list)

    # validate
    p_val = subparsers.add_parser("validate", help="Validate scenario schemas")
    p_val.add_argument("--dataset", "-d", default="v1", help="Dataset version (default: v1)")
    p_val.set_defaults(func=cmd_validate)

    # run
    p_run = subparsers.add_parser("run", help="Run benchmark scenarios")
    p_run.add_argument("--dataset", "-d", default="v1", help="Dataset version (default: v1)")
    p_run.add_argument("--scenario", "-s", help="Specific scenario ID to run")
    p_run.add_argument("--category", "-c", help="Filter scenarios by category")
    p_run.add_argument("--language", "-l", help="Filter scenarios by language")
    p_run.add_argument("--name", "-n", default="benchmark-run", help="Name of the run")
    p_run.add_argument("--concurrency", type=int, default=1, help="Max concurrency (default: 1)")
    p_run.add_argument("--ablation", "-a", help="Run in ablation mode")
    p_run.add_argument("--export-md", help="Path to write Markdown report")
    p_run.add_argument("--export-json", help="Path to write JSON report")
    p_run.add_argument("--export-csv", help="Path to write CSV report")
    p_run.set_defaults(func=cmd_run)

    # regression
    p_reg = subparsers.add_parser("regression", help="Run benchmark regression analysis")
    p_reg.add_argument("--baseline", "-b", default="benchmark_report.json", help="Path to baseline JSON report")
    p_reg.add_argument("--candidate", help="Path to candidate JSON report (if omitted, runs scenarios)")
    p_reg.add_argument("--dataset", "-d", default="v1", help="Dataset version (default: v1)")
    p_reg.add_argument("--concurrency", type=int, default=4, help="Max concurrency (default: 4)")
    p_reg.add_argument("--f1-tolerance", type=float, default=0.05, help="Allowable F1 drop (default: 0.05)")
    p_reg.add_argument("--precision-tolerance", type=float, default=0.05, help="Allowable precision drop (default: 0.05)")
    p_reg.add_argument("--recall-tolerance", type=float, default=0.05, help="Allowable recall drop (default: 0.05)")
    p_reg.set_defaults(func=cmd_regression)

    return parser


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    code = args.func(args)
    sys.exit(code)


if __name__ == "__main__":
    main()
