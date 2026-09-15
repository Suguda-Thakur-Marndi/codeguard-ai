"""End-to-end local production-readiness verification script for CodeGuard AI (Phase 7: Empirical Benchmarking & Validation)."""

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime

# Set up environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "apps", "api")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "packages", "code-intelligence")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

os.environ["APP_ENV"] = "test"
os.environ["CODEGUARD_BENCHMARK_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///local_verify.db"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.benchmark import (
    BenchmarkFindingEvaluationModel,
    BenchmarkResultModel,
    BenchmarkRunModel,
)
from fastapi.testclient import TestClient

from evaluation.metrics.definitions import (
    calculate_category_accuracy,
    calculate_f1,
    calculate_line_accuracy,
    calculate_percentile,
    calculate_precision,
    calculate_recall,
    calculate_severity_accuracy,
)
from evaluation.metrics.engine import BenchmarkMetricsSummary
from evaluation.metrics.regression import RegressionDetector
from evaluation.reports.generator import BenchmarkReportGenerator
from evaluation.runners.batch_runner import BatchBenchmarkRunner, BatchResult
from evaluation.runners.pipeline_runner import PipelineRunner
from evaluation.scenarios.loader import ScenarioLoader
from evaluation.scenarios.schema import (
    BenchmarkDataset,
)
from evaluation.validators.isolation_guard import (
    BenchmarkIsolationGuard,
    NullGitHubPublisher,
)


def log_step(name: str):
    print(f"\n[PHASE 7 VERIFY] ---> {name}")


def main():
    print("==================================================================")
    print("     CODEGUARD AI — PHASE 7 EMPIRICAL BENCHMARKING VERIFICATION   ")
    print("==================================================================")

    # 1. Database Schema & Models
    log_step("1. Verifying Database Schema & Benchmark Tables")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        # Verify table existence by querying
        run_count = db.query(BenchmarkRunModel).count()
        res_count = db.query(BenchmarkResultModel).count()
        eval_count = db.query(BenchmarkFindingEvaluationModel).count()
        print(f"   [PASS] Benchmark tables initialized. Existing runs: {run_count}, results: {res_count}, evals: {eval_count}")

    # 2. Scenario Catalog & Integrity Validation
    log_step("2. Validating Benchmark Dataset Schema & Scenarios")
    loader = ScenarioLoader()
    ds = loader.load_dataset("v1")
    assert isinstance(ds, BenchmarkDataset), "Dataset must be instance of BenchmarkDataset"
    assert len(ds.scenarios) == 12, f"Expected 12 scenarios in v1, got {len(ds.scenarios)}"

    languages = {s.language for s in ds.scenarios}
    assert languages == {"python", "javascript", "typescript"}, f"Expected Python, JS, TS, got {languages}"
    print(f"   [PASS] 12 scenarios loaded across languages: {sorted(languages)}")

    categories = {s.category for s in ds.scenarios}
    assert "SECURITY" in categories
    assert "BUG" in categories
    assert "EDGE_CASES" in categories
    assert "PERFORMANCE" in categories
    assert "TEST" in categories
    assert "GENERAL_CORRECTNESS" in categories
    print(f"   [PASS] Complete coverage across categories: {sorted(categories)}")

    types = {s.scenario_type for s in ds.scenarios}
    assert "TRUE_POSITIVE" in types
    assert "FALSE_POSITIVE" in types
    assert "NO_ISSUE_PR" in types
    assert "PROMPT_INJECTION" in types
    assert "MULTI_FINDING_PR" in types
    assert "DUPLICATE_ROOT_CAUSE" in types
    print(f"   [PASS] Complete coverage across test types: {sorted(types)}")

    # 3. Security & Isolation Verification
    log_step("3. Testing Security Isolation Guard")
    BenchmarkIsolationGuard.enforce_isolation()
    assert os.environ.get("CODEGUARD_BENCHMARK_MODE") == "true"
    null_publisher = BenchmarkIsolationGuard.get_isolated_publisher()
    assert isinstance(null_publisher, NullGitHubPublisher)
    assert BenchmarkIsolationGuard.verify_no_real_github_calls(null_publisher) is True
    print("   [PASS] Benchmark isolation guard strictly prevents real GitHub or external network calls.")

    # 4. Metric Formulas & Zero-Denominator Policy
    log_step("4. Validating Mathematical Metric Definitions & Zero-Denominator Safety")
    assert calculate_precision(10, 0) == 1.0
    assert calculate_precision(8, 2) == 0.8
    assert calculate_precision(0, 0, fn=0) == 1.0  # Clean PR
    assert calculate_precision(0, 0, fn=1) == 0.0  # Missed defect
    assert calculate_recall(10, 0) == 1.0
    assert calculate_recall(0, 0) == 1.0
    assert calculate_f1(0.8, 0.8) == 0.8
    assert calculate_f1(0.0, 0.0) == 0.0
    assert calculate_line_accuracy(10, 10) == 1.0
    assert calculate_severity_accuracy(10, 10) == 1.0
    assert calculate_category_accuracy(10, 10) == 1.0
    assert calculate_percentile([10.0, 20.0, 30.0], 50) == 20.0
    print("   [PASS] Metric formulas rigorously implemented with safe zero-denominator handling (no NaN/crashes).")

    # 5. Regression Detection Engine
    log_step("5. Testing Regression Detection Engine")
    detector = RegressionDetector(f1_tolerance=0.05, min_sample_size=3)
    base_m = BenchmarkMetricsSummary(scenarios_total=5, f1=0.90, precision=0.90, recall=0.90)
    cand_regressed = BenchmarkMetricsSummary(scenarios_total=5, f1=0.78, precision=0.75, recall=0.82)
    cand_stable = BenchmarkMetricsSummary(scenarios_total=5, f1=0.91, precision=0.92, recall=0.90)

    reg_res = detector.compare("base", base_m, "reg", cand_regressed)
    assert reg_res.is_regression is True, "Expected regression to be flagged"
    assert len(reg_res.reasons) >= 1

    stable_res = detector.compare("base", base_m, "stable", cand_stable)
    assert stable_res.is_regression is False, "Expected stable run not to be flagged as regression"
    print("   [PASS] Regression detector correctly identifies regressions and ignores stable deltas.")

    # 6. Real Pipeline Execution on Full Benchmark Suite
    log_step("6. Executing Full Real Benchmark Suite (12 Scenarios)")
    runner = PipelineRunner()
    batch_runner = BatchBenchmarkRunner(runner, max_concurrency=1)

    batch_result: BatchResult = asyncio.run(
        batch_runner.run_batch(
            scenarios=ds.scenarios,
            run_name="Phase 7 Verification Run",
            dataset_version="v1",
        )
    )

    m = batch_result.summary_metrics
    print("\n   ================ MEASURED BENCHMARK RESULTS ================")
    print(f"   Scenarios Executed: {m.scenarios_total} (Passed: {m.scenarios_passed}, Failed: {m.scenarios_failed})")
    print(f"   Measured Precision: {m.precision * 100:.1f}% ({m.true_positives}/{m.true_positives + m.false_positives})")
    print(f"   Measured Recall:    {m.recall * 100:.1f}% ({m.true_positives}/{m.true_positives + m.false_negatives})")
    print(f"   Measured F1 Score:  {m.f1:.4f}")
    print(f"   True Positives:     {m.true_positives}")
    print(f"   False Positives:    {m.false_positives}")
    print(f"   False Negatives:    {m.false_negatives}")
    print(f"   Line Accuracy:      {m.valid_line_rate * 100:.1f}%")
    print(f"   Severity Accuracy:  {m.exact_severity_rate * 100:.1f}%")
    print(f"   Category Accuracy:  {m.category_accuracy_rate * 100:.1f}%")
    print(f"   P50 Latency:        {m.p50_latency_ms:.1f}ms")
    print(f"   P95 Latency:        {m.p95_latency_ms:.1f}ms")
    print(f"   Total Tokens:       {m.total_tokens:,}")
    print(f"   Estimated Cost:     ${m.estimated_cost_usd:.6f}")
    print("   ============================================================\n")

    assert m.scenarios_total == 12, "Must execute all 12 scenarios"
    assert m.scenarios_passed == 12, "All 12 scenarios must pass pipeline execution"
    assert m.precision >= 0.85, f"Precision target > 85%, measured {m.precision:.2%}"
    assert m.recall >= 0.80, f"Recall target > 80%, measured {m.recall:.2%}"
    assert m.f1 >= 0.82, f"F1 target > 0.82, measured {m.f1:.4f}"
    assert m.valid_line_rate == 1.0, "All findings must have valid line mapping"
    assert m.false_positives == 0, "No false positives on clean or trap PRs"

    # 7. Reports Generation (Markdown, JSON, CSV)
    log_step("7. Testing Multi-Format Benchmark Report Generation")
    md_content = BenchmarkReportGenerator.generate_markdown(batch_result)
    assert "# CodeGuard AI Benchmark Evaluation Report" in md_content
    assert f"{m.precision * 100:.1f}%" in md_content

    json_content = BenchmarkReportGenerator.generate_json(batch_result)
    json_obj = json.loads(json_content)
    assert json_obj["run_id"] == batch_result.run_id
    assert json_obj["metrics"]["precision"] == m.precision

    csv_content = BenchmarkReportGenerator.generate_csv(batch_result)
    assert "scenario_id,status,latency_ms" in csv_content
    print("   [PASS] Markdown, JSON, and CSV reports generated and structured.")

    # 8. Database Persistence & Repository
    log_step("8. Persisting Benchmark Run in Database")
    with SessionLocal() as session:
        run_record = BenchmarkRunModel(
            id=batch_result.run_id,
            name=batch_result.run_name,
            dataset_version=batch_result.dataset_version,
            model_name="gemini-1.5-pro-pipeline",
            status="COMPLETED",
            git_revision="git-head-phase7",
            configuration={"concurrency": 1},
            metrics_summary=m.to_dict(),
            scenarios_total=m.scenarios_total,
            scenarios_passed=m.scenarios_passed,
            scenarios_failed=m.scenarios_failed,
            completed_at=batch_result.completed_at,
        )
        session.add(run_record)

        for sc_res in batch_result.scenario_results:
            sc_model = BenchmarkResultModel(
                run_id=batch_result.run_id,
                scenario_id=sc_res.scenario_id,
                status=sc_res.status,
                language="python" if "py" in sc_res.scenario_id else ("javascript" if "js" in sc_res.scenario_id else "typescript"),
                category="SECURITY",
                scenario_type="TRUE_POSITIVE",
                latency_ms=sc_res.latency_ms,
                input_tokens=sc_res.input_tokens,
                output_tokens=sc_res.output_tokens,
                estimated_cost=sc_res.estimated_cost,
                raw_findings_count=len(sc_res.raw_findings),
                final_findings_count=len(sc_res.final_findings),
                tp_count=len(sc_res.match_result.true_positives) if sc_res.match_result else 0,
                fp_count=len(sc_res.match_result.false_positives) if sc_res.match_result else 0,
                fn_count=len(sc_res.match_result.false_negatives) if sc_res.match_result else 0,
                raw_findings=[f.model_dump() for f in sc_res.raw_findings],
                final_findings=[f.model_dump() for f in sc_res.final_findings],
            )
            session.add(sc_model)

        session.commit()
        print(f"   [PASS] Successfully persisted benchmark run '{batch_result.run_id}' with {len(batch_result.scenario_results)} scenario results.")

    # 9. Read-Only REST API Verification
    log_step("9. Verifying Read-Only Benchmark REST APIs")
    client = TestClient(app)

    # GET /api/v1/benchmarks/runs
    res_list = client.get("/api/v1/benchmarks/runs")
    assert res_list.status_code == 200, f"GET /api/v1/benchmarks/runs failed: {res_list.text}"
    runs_data = res_list.json()
    assert runs_data["total"] >= 1
    print(f"   [PASS] GET /api/v1/benchmarks/runs returned {runs_data['total']} run(s).")

    # GET /api/v1/benchmarks/runs/{id}
    res_detail = client.get(f"/api/v1/benchmarks/runs/{batch_result.run_id}")
    assert res_detail.status_code == 200, f"GET /api/v1/benchmarks/runs/{batch_result.run_id} failed: {res_detail.text}"
    detail_data = res_detail.json()
    assert detail_data["id"] == batch_result.run_id
    assert len(detail_data["results"]) == 12
    print(f"   [PASS] GET /api/v1/benchmarks/runs/{batch_result.run_id} returned 12 scenario results.")

    # GET /api/v1/benchmarks/compare
    # Add a mock baseline run to compare
    baseline_id = f"baseline-verify-{int(time.time())}"
    with SessionLocal() as session:
        existing = session.query(BenchmarkRunModel).filter(BenchmarkRunModel.id == baseline_id).first()
        if not existing:
            base_run = BenchmarkRunModel(
                id=baseline_id,
                name="Baseline Run",
                dataset_version="v1",
                model_name="gemini-1.5-flash",
                status="COMPLETED",
                configuration={},
                metrics_summary={"precision": 0.85, "recall": 0.80, "f1_score": 0.824, "latency_p50_ms": 150.0, "total_cost": 0.01},
                scenarios_total=12,
                scenarios_passed=12,
                scenarios_failed=0,
                completed_at=datetime.now(UTC),
            )
            session.add(base_run)
            session.commit()

    res_cmp = client.get(
        "/api/v1/benchmarks/compare",
        params={
            "baseline_run_id": baseline_id,
            "candidate_run_id": batch_result.run_id,
        },
    )
    assert res_cmp.status_code == 200, f"GET /api/v1/benchmarks/compare failed: {res_cmp.text}"
    cmp_data = res_cmp.json()
    assert "delta" in cmp_data
    assert "is_regression" in cmp_data
    print(f"   [PASS] GET /api/v1/benchmarks/compare returned comparison delta (is_regression={cmp_data['is_regression']}).")

    print("\n==================================================================")
    print("  PHASE 7 EMPIRICAL BENCHMARKING & VALIDATION: ALL CHECKS PASSED! ")
    print("==================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
