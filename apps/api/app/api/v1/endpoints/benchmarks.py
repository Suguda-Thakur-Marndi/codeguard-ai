"""Read-only REST API endpoints for Benchmark evaluations, runs, and regression analysis."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user_or_bypass
from app.db.repositories.benchmark_repo import (
    BenchmarkRunRepository,
)
from app.db.session import get_db

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("/runs", response_model=dict[str, Any])
def list_benchmark_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_or_bypass),
) -> dict[str, Any]:
    """List benchmark execution runs ordered by creation date descending."""
    repo = BenchmarkRunRepository(db)
    items, total = repo.list_runs(page=page, page_size=page_size)

    return {
        "items": [
            {
                "id": run.id,
                "name": run.name,
                "dataset_version": run.dataset_version,
                "model_name": run.model_name,
                "status": run.status,
                "git_revision": run.git_revision,
                "scenarios_total": run.scenarios_total,
                "scenarios_passed": run.scenarios_passed,
                "scenarios_failed": run.scenarios_failed,
                "metrics_summary": run.metrics_summary,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "created_at": run.created_at.isoformat(),
            }
            for run in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/runs/{run_id}", response_model=dict[str, Any])
def get_benchmark_run(
    run_id: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_or_bypass),
) -> dict[str, Any]:
    """Get full details of a specific benchmark run, including scenario results and evaluations."""
    repo = BenchmarkRunRepository(db)
    run = repo.get_run_with_results(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark run '{run_id}' not found",
        )

    return {
        "id": run.id,
        "name": run.name,
        "dataset_version": run.dataset_version,
        "model_name": run.model_name,
        "status": run.status,
        "git_revision": run.git_revision,
        "configuration": run.configuration,
        "metrics_summary": run.metrics_summary,
        "scenarios_total": run.scenarios_total,
        "scenarios_passed": run.scenarios_passed,
        "scenarios_failed": run.scenarios_failed,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat(),
        "results": [
            {
                "id": r.id,
                "scenario_id": r.scenario_id,
                "status": r.status,
                "language": r.language,
                "category": r.category,
                "scenario_type": r.scenario_type,
                "latency_ms": r.latency_ms,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "estimated_cost": r.estimated_cost,
                "raw_findings_count": r.raw_findings_count,
                "final_findings_count": r.final_findings_count,
                "tp_count": r.tp_count,
                "fp_count": r.fp_count,
                "fn_count": r.fn_count,
                "error_message": r.error_message,
                "evaluations": [
                    {
                        "finding_id": ev.finding_id,
                        "classification": ev.classification,
                        "predicted_category": ev.predicted_category,
                        "expected_category": ev.expected_category,
                        "category_matched": ev.category_matched,
                        "predicted_severity": ev.predicted_severity,
                        "expected_severity": ev.expected_severity,
                        "severity_matched": ev.severity_matched,
                        "line_matched": ev.line_matched,
                        "semantic_similarity": ev.semantic_similarity,
                        "reasons": ev.reasons,
                    }
                    for ev in r.evaluations
                ],
            }
            for r in run.results
        ],
    }


@router.get("/compare", response_model=dict[str, Any])
def compare_benchmark_runs(
    baseline_run_id: str = Query(..., description="ID of baseline benchmark run"),
    candidate_run_id: str = Query(..., description="ID of candidate benchmark run"),
    db: Session = Depends(get_db),
    _user: dict = Depends(get_current_user_or_bypass),
) -> dict[str, Any]:
    """Compare two benchmark runs and calculate delta metrics and regression analysis."""
    repo = BenchmarkRunRepository(db)
    baseline = repo.get_by_id(baseline_run_id)
    candidate = repo.get_by_id(candidate_run_id)

    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Baseline benchmark run '{baseline_run_id}' not found",
        )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate benchmark run '{candidate_run_id}' not found",
        )

    base_summary = baseline.metrics_summary or {}
    cand_summary = candidate.metrics_summary or {}

    def get_val(summary: dict[str, Any], key: str) -> float:
        v = summary.get(key, 0.0)
        return float(v) if v is not None else 0.0

    delta = {
        "precision_delta": round(get_val(cand_summary, "precision") - get_val(base_summary, "precision"), 4),
        "recall_delta": round(get_val(cand_summary, "recall") - get_val(base_summary, "recall"), 4),
        "f1_delta": round(get_val(cand_summary, "f1_score") - get_val(base_summary, "f1_score"), 4),
        "latency_p50_delta_ms": round(get_val(cand_summary, "latency_p50_ms") - get_val(base_summary, "latency_p50_ms"), 2),
        "total_cost_delta": round(get_val(cand_summary, "total_cost") - get_val(base_summary, "total_cost"), 6),
    }

    # Identify regressions
    regressions = []
    if delta["f1_delta"] < -0.05:
        regressions.append(f"F1 score degraded by {abs(delta['f1_delta']):.2%}")
    if delta["precision_delta"] < -0.05:
        regressions.append(f"Precision degraded by {abs(delta['precision_delta']):.2%}")
    if delta["recall_delta"] < -0.05:
        regressions.append(f"Recall degraded by {abs(delta['recall_delta']):.2%}")

    return {
        "baseline_run": {
            "id": baseline.id,
            "name": baseline.name,
            "metrics": base_summary,
        },
        "candidate_run": {
            "id": candidate.id,
            "name": candidate.name,
            "metrics": cand_summary,
        },
        "delta": delta,
        "is_regression": len(regressions) > 0,
        "regressions": regressions,
    }
