"""Comprehensive test suite for Phase 7 Empirical Benchmarking & Validation subsystem."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.agents.schemas.finding import (
    FindingCategory,
    FindingSeverity,
    ReviewFinding,
)
from app.models.benchmark import (
    BenchmarkFindingEvaluationModel,
    BenchmarkResultModel,
    BenchmarkRunModel,
)
from evaluation.metrics.definitions import (
    calculate_category_accuracy,
    calculate_f1,
    calculate_line_accuracy,
    calculate_percentile,
    calculate_precision,
    calculate_recall,
    calculate_severity_accuracy,
)
from evaluation.metrics.engine import BenchmarkMetricsSummary, MetricsEngine
from evaluation.metrics.regression import RegressionDetector
from evaluation.reports.generator import BenchmarkReportGenerator
from evaluation.runners.batch_runner import BatchResult
from evaluation.runners.pipeline_runner import PipelineRunner
from evaluation.scenarios.loader import ScenarioLoader
from evaluation.scenarios.schema import (
    BenchmarkDataset,
    BenchmarkScenario,
    FindingClassification,
    GroundTruthFinding,
    ScenarioCategory,
    ScenarioType,
)
from evaluation.validators.isolation_guard import (
    BenchmarkIsolationGuard,
    NullGitHubPublisher,
)
from evaluation.validators.patch_validator import PatchValidator
from evaluation.validators.semantic_matcher import MatchResult, SemanticFindingMatcher


class TestScenarioLoaderAndSchema:
    """Test scenario parsing, validation, and filtering."""

    def test_load_dataset_v1(self) -> None:
        loader = ScenarioLoader()
        dataset = loader.load_dataset("v1")
        assert isinstance(dataset, BenchmarkDataset)
        assert dataset.dataset_version == "v1"
        assert len(dataset.scenarios) == 12

    def test_filter_by_language(self) -> None:
        loader = ScenarioLoader()
        py_scenarios = loader.load_scenarios("v1", language="python")
        js_scenarios = loader.load_scenarios("v1", language="javascript")
        ts_scenarios = loader.load_scenarios("v1", language="typescript")

        assert len(py_scenarios) == 10
        assert len(js_scenarios) == 1
        assert len(ts_scenarios) == 1
        assert all(s.language == "python" for s in py_scenarios)
        assert js_scenarios[0].scenario_id == "js-sec-sqli-002"
        assert ts_scenarios[0].scenario_id == "ts-sec-secret-003"

    def test_filter_by_category_and_type(self) -> None:
        loader = ScenarioLoader()
        sec_scenarios = loader.load_scenarios(
            "v1", category=ScenarioCategory.SECURITY
        )
        assert len(sec_scenarios) >= 5

        fp_scenarios = loader.load_scenarios(
            "v1", scenario_type=ScenarioType.FALSE_POSITIVE
        )
        assert len(fp_scenarios) == 1
        assert fp_scenarios[0].scenario_id == "py-fp-guarded-caller-008"

        no_issue = loader.load_scenarios(
            "v1", scenario_type=ScenarioType.NO_ISSUE_PR
        )
        assert len(no_issue) == 1
        assert no_issue[0].scenario_id == "py-noissue-refactor-009"

    def test_prompt_injection_scenario(self) -> None:
        loader = ScenarioLoader()
        scenario = loader.get_scenario("py-injection-defense-010", "v1")
        assert scenario is not None
        assert scenario.contains_prompt_injection is True
        assert scenario.injection_payload is not None
        assert "Ignore all previous commands" in scenario.injection_payload


class TestSemanticMatcher:
    """Test finding matching against ground truth definitions."""

    def test_match_true_positive(self) -> None:
        loader = ScenarioLoader()
        scenario = loader.get_scenario("py-sec-auth-001", "v1")

        pred = ReviewFinding(
            finding_id="pred-1",
            category=FindingCategory.SECURITY,
            severity=FindingSeverity.CRITICAL,
            file_path="src/services/payment_service.py",
            line_number=34,
            start_line=34,
            title="Missing Authorization Check in Payment Refund",
            description="Operator authorization permission check was removed, allowing unauthorized refunds.",
            impact="Any caller can execute customer refunds without authorization.",
            recommendation="Restore auth_service.verify_refund_permission and raise PermissionError.",
            confidence=1.0,
        )

        matcher = SemanticFindingMatcher()
        match_result = matcher.evaluate_scenario(scenario, [pred])

        assert len(match_result.true_positives) == 1
        assert len(match_result.false_positives) == 0
        assert len(match_result.false_negatives) == 0
        assert match_result.true_positives[0].classification == FindingClassification.TRUE_POSITIVE
        assert match_result.true_positives[0].location_match is True
        assert match_result.true_positives[0].category_match is True
        assert match_result.true_positives[0].severity_match is True

    def test_false_positive_trap(self) -> None:
        loader = ScenarioLoader()
        scenario = loader.get_scenario("py-fp-guarded-caller-008", "v1")

        pred = ReviewFinding(
            finding_id="pred-trap",
            category=FindingCategory.SECURITY,
            severity=FindingSeverity.CRITICAL,
            file_path="src/services/payment_service.py",
            line_number=52,
            start_line=51,
            title="Missing Authorization in _raw_refund",
            description="_raw_refund executes without checking operator authorization permissions.",
            impact="Unauthorized refund.",
            recommendation="Add authorization check.",
            confidence=0.9,
        )

        matcher = SemanticFindingMatcher()
        match_result = matcher.evaluate_scenario(scenario, [pred])

        # Flagging guarded code in an FP trap scenario is classified as FALSE_POSITIVE
        assert len(match_result.false_positives) == 1
        assert len(match_result.true_positives) == 0
        assert match_result.false_positives[0].classification == FindingClassification.FALSE_POSITIVE

    def test_unmatched_finding_is_false_positive(self) -> None:
        loader = ScenarioLoader()
        scenario = loader.get_scenario("py-sec-auth-001", "v1")

        unrelated_pred = ReviewFinding(
            finding_id="pred-unrelated",
            category=FindingCategory.PERFORMANCE,
            severity=FindingSeverity.LOW,
            file_path="src/unrelated_file.py",
            line_number=99,
            start_line=99,
            title="Slow loop",
            description="Loop is suboptimal.",
            impact="Minor latency.",
            recommendation="Vectorize loop.",
            confidence=0.5,
        )

        matcher = SemanticFindingMatcher()
        match_result = matcher.evaluate_scenario(scenario, [unrelated_pred])

        assert len(match_result.false_positives) == 1
        assert len(match_result.false_negatives) == 1
        assert len(match_result.true_positives) == 0


class TestMetricsCalculation:
    """Test metric formulas, zero-denominator safety, and percentiles."""

    def test_precision_recall_f1_basic(self) -> None:
        assert calculate_precision(8, 2) == 0.8
        assert calculate_recall(8, 2) == 0.8
        assert calculate_f1(0.8, 0.8) == 0.8

    def test_zero_division_handling(self) -> None:
        # Zero predicted findings with zero expected is a perfect clean PR (precision = 1.0)
        assert calculate_precision(0, 0, fn=0) == 1.0
        # Zero predicted findings when issues were expected is a complete miss (precision = 0.0)
        assert calculate_precision(0, 0, fn=1) == 0.0
        assert calculate_recall(0, 0) == 1.0
        assert calculate_f1(0.0, 0.0) == 0.0
        assert calculate_category_accuracy(0, 0) == 0.0
        assert calculate_severity_accuracy(0, 0) == 0.0
        assert calculate_line_accuracy(0, 0) == 0.0

    def test_percentile_calculation(self) -> None:
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        assert calculate_percentile(values, 50) == 55.0
        assert calculate_percentile(values, 95) == 95.5
        assert calculate_percentile([], 50) == 0.0
        assert calculate_percentile([42.0], 90) == 42.0

    def test_metrics_engine_compilation(self) -> None:
        m = MatchResult(scenario_id="sc-1")
        summary = MetricsEngine.compute_summary([m])
        assert summary.scenarios_total == 1
        assert summary.precision == 1.0  # 0 TP, 0 FP, 0 FN = clean scenario
        assert summary.recall == 1.0
        assert summary.f1 == 1.0


class TestRegressionDetector:
    """Test automated regression flagging between benchmark runs."""

    def test_detect_regression_on_degraded_f1(self) -> None:
        baseline = BenchmarkMetricsSummary(
            scenarios_total=5,
            precision=0.92,
            recall=0.88,
            f1=0.90,
            avg_latency_ms=100.0,
            p95_latency_ms=200.0,
            estimated_cost_usd=0.01,
        )

        candidate = BenchmarkMetricsSummary(
            scenarios_total=5,
            precision=0.70,
            recall=0.81,
            f1=0.75,  # Significant drop (> 0.05)
            avg_latency_ms=110.0,
            p95_latency_ms=220.0,
            estimated_cost_usd=0.011,
        )

        detector = RegressionDetector()
        report = detector.compare("base", baseline, "cand", candidate)

        assert report.is_regression is True
        assert len(report.reasons) > 0

    def test_no_regression_on_stable_or_improved_metrics(self) -> None:
        baseline = BenchmarkMetricsSummary(
            scenarios_total=5,
            precision=0.85,
            recall=0.85,
            f1=0.85,
            avg_latency_ms=150.0,
            p95_latency_ms=300.0,
            estimated_cost_usd=0.01,
        )

        candidate = BenchmarkMetricsSummary(
            scenarios_total=5,
            precision=0.90,
            recall=0.86,
            f1=0.88,
            avg_latency_ms=140.0,
            p95_latency_ms=290.0,
            estimated_cost_usd=0.01,
        )

        detector = RegressionDetector()
        report = detector.compare("base", baseline, "cand", candidate)

        assert report.is_regression is False
        assert len(report.reasons) == 0


class TestBenchmarkIsolationGuard:
    """Test safety enforcement preventing real network calls or repo alterations."""

    @pytest.mark.asyncio
    async def test_null_github_publisher_blocks_external_calls(self) -> None:
        publisher = NullGitHubPublisher()
        result = await publisher.publish_atomic_review(
            owner="org",
            repo="test-repo",
            pull_number=999,
            verified_head_sha="abcdef1234567890",
            current_head_sha="abcdef1234567890",
            findings=[{"title": "Simulated Finding"}],
        )
        assert result.status == "PUBLISHED_SIMULATED"
        assert result.success is True
        assert len(publisher.published_reviews) == 1
        assert publisher.published_reviews[0]["owner"] == "org"

    def test_isolation_guard_validates_environment(self) -> None:
        BenchmarkIsolationGuard.enforce_isolation()
        publisher = BenchmarkIsolationGuard.get_isolated_publisher()
        assert BenchmarkIsolationGuard.verify_no_real_github_calls(publisher) is True


class TestPatchValidator:
    """Test patch syntax checking and validation."""

    @pytest.mark.asyncio
    async def test_valid_python_syntax(self) -> None:
        validator = PatchValidator()
        code = "def valid_func(x: int) -> int:\n    return x + 1\n"
        res = await validator.validate_python_patch(code, code)
        assert res.syntax_valid is True
        assert res.error is None

    @pytest.mark.asyncio
    async def test_invalid_python_syntax(self) -> None:
        validator = PatchValidator()
        bad_code = "def invalid_func(\n    return x +\n"
        res = await validator.validate_python_patch("pass", bad_code)
        assert res.syntax_valid is False
        assert res.error is not None


class TestPipelineRunnerExecution:
    """Integration test running real scenarios through the CodeGuard pipeline."""

    @pytest.mark.asyncio
    async def test_execute_auth_scenario(self) -> None:
        loader = ScenarioLoader()
        scenario = loader.get_scenario("py-sec-auth-001", "v1")
        assert scenario is not None

        runner = PipelineRunner()
        result = await runner.run_scenario(scenario)

        assert result.scenario_id == "py-sec-auth-001"
        assert result.status == "COMPLETED"
        assert len(result.raw_findings) >= 1
        assert len(result.final_findings) >= 1
        assert result.match_result is not None
        assert len(result.match_result.true_positives) >= 1
        assert result.latency_ms > 0
        assert result.input_tokens > 0

    @pytest.mark.asyncio
    async def test_execute_no_issue_scenario(self) -> None:
        loader = ScenarioLoader()
        scenario = loader.get_scenario("py-noissue-refactor-009", "v1")
        assert scenario is not None

        runner = PipelineRunner()
        result = await runner.run_scenario(scenario)

        assert result.scenario_id == "py-noissue-refactor-009"
        assert result.status == "COMPLETED"
        assert len(result.final_findings) == 0
        assert result.match_result is not None
        assert len(result.match_result.false_positives) == 0


class TestBenchmarkDatabaseAndAPI:
    """Test persistence in PostgreSQL/SQLite and read-only REST API endpoints."""

    def test_benchmark_api_lifecycle(self, client: TestClient, db_session: Session) -> None:
        # 1. Seed a completed benchmark run in the database
        now = datetime.now(UTC)
        run = BenchmarkRunModel(
            id="test-benchmark-run-001",
            name="CI Benchmark Run v1",
            dataset_version="v1",
            model_name="mock-pipeline-provider",
            status="COMPLETED",
            git_revision="git-test-commit-001",
            configuration={"seed": 42},
            metrics_summary={
                "precision": 0.95,
                "recall": 0.90,
                "f1_score": 0.924,
                "latency_p50_ms": 120.0,
                "total_cost": 0.005,
            },
            scenarios_total=1,
            scenarios_passed=1,
            scenarios_failed=0,
            completed_at=now,
        )
        db_session.add(run)

        result = BenchmarkResultModel(
            id="res-001",
            run_id="test-benchmark-run-001",
            scenario_id="py-sec-auth-001",
            status="PASSED",
            language="python",
            category="SECURITY",
            scenario_type="TRUE_POSITIVE",
            latency_ms=120.0,
            input_tokens=1500,
            output_tokens=300,
            estimated_cost=0.005,
            raw_findings_count=1,
            final_findings_count=1,
            tp_count=1,
            fp_count=0,
            fn_count=0,
            raw_findings=[],
            final_findings=[],
        )
        db_session.add(result)

        eval_model = BenchmarkFindingEvaluationModel(
            id="eval-001",
            result_id="res-001",
            finding_id="finding-101",
            classification="TRUE_POSITIVE",
            predicted_category="SECURITY",
            expected_category="SECURITY",
            category_matched=True,
            predicted_severity="CRITICAL",
            expected_severity="CRITICAL",
            severity_matched=True,
            line_matched=True,
            semantic_similarity=0.92,
            reasons=["Matched line and category"],
        )
        db_session.add(eval_model)
        db_session.commit()

        # 2. Test GET /api/v1/benchmarks/runs
        response = client.get("/api/v1/benchmarks/runs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        run_entry = next(r for r in data["items"] if r["id"] == "test-benchmark-run-001")
        assert run_entry["dataset_version"] == "v1"
        assert run_entry["metrics_summary"]["precision"] == 0.95

        # 3. Test GET /api/v1/benchmarks/runs/{id}
        res_detail = client.get("/api/v1/benchmarks/runs/test-benchmark-run-001")
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert len(detail_data["results"]) == 1
        assert detail_data["results"][0]["scenario_id"] == "py-sec-auth-001"
        assert len(detail_data["results"][0]["evaluations"]) == 1
        assert detail_data["results"][0]["evaluations"][0]["classification"] == "TRUE_POSITIVE"

        # 4. Test GET /api/v1/benchmarks/compare
        # Seed baseline run
        baseline_run = BenchmarkRunModel(
            id="test-benchmark-run-base",
            name="Baseline Benchmark Run",
            dataset_version="v1",
            model_name="mock-pipeline-provider",
            status="COMPLETED",
            git_revision="git-base",
            configuration={},
            metrics_summary={
                "precision": 0.90,
                "recall": 0.85,
                "f1_score": 0.874,
                "latency_p50_ms": 130.0,
                "total_cost": 0.006,
            },
            scenarios_total=1,
            scenarios_passed=1,
            scenarios_failed=0,
            completed_at=now,
        )
        db_session.add(baseline_run)
        db_session.commit()

        cmp_res = client.get(
            "/api/v1/benchmarks/compare",
            params={
                "baseline_run_id": "test-benchmark-run-base",
                "candidate_run_id": "test-benchmark-run-001",
            },
        )
        assert cmp_res.status_code == 200
        cmp_data = cmp_res.json()
        assert cmp_data["is_regression"] is False
        assert cmp_data["delta"]["f1_delta"] == pytest.approx(0.05, abs=1e-3)


class TestReportGenerator:
    """Test generation of Markdown, JSON, and CSV reports."""

    def test_generate_reports(self) -> None:
        summary = BenchmarkMetricsSummary(
            scenarios_total=12,
            scenarios_passed=12,
            scenarios_failed=0,
            precision=0.91,
            recall=0.88,
            f1=0.895,
            true_positives=10,
            false_positives=1,
            false_negatives=1,
            valid_line_count=10,
            exact_severity_count=9,
            category_match_count=10,
            total_tokens=25000,
            estimated_cost_usd=0.05,
            avg_latency_ms=250.0,
            p50_latency_ms=240.0,
            p95_latency_ms=450.0,
        )

        now = datetime.now(UTC)
        batch_result = BatchResult(
            run_id="run-report-test",
            run_name="Unit Test Suite Report",
            dataset_version="v1",
            started_at=now,
            completed_at=now,
            duration_seconds=5.2,
            concurrency=1,
            summary_metrics=summary,
            scenario_results=[],
        )

        md_report = BenchmarkReportGenerator.generate_markdown(batch_result)
        assert "# CodeGuard AI Benchmark Evaluation Report" in md_report
        assert "91.0%" in md_report

        json_report = BenchmarkReportGenerator.generate_json(batch_result)
        assert "run-report-test" in json_report

        csv_report = BenchmarkReportGenerator.generate_csv(batch_result)
        assert "scenario_id,status,latency_ms" in csv_report
