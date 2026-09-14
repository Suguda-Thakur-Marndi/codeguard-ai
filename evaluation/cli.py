"""Command Line Interface for CodeGuard AI Empirical Benchmark Suite."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from evaluation.metrics.regression import RegressionDetector
from evaluation.reports.generator import BenchmarkReportGenerator
from evaluation.runners.ablation_runner import AblationConfig, AblationRunner
from evaluation.runners.batch_runner import BatchBenchmarkRunner
from evaluation.runners.pipeline_runner import PipelineRunner
from evaluation.scenarios.loader import ScenarioLoader
from evaluation.scenarios.schema import BenchmarkScenario


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
    except Exception as exc:
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

    return parser


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    code = args.func(args)
    sys.exit(code)


if __name__ == "__main__":
    main()
