"""API schemas for Phase 4 Adversarial Verification and Execution-Grounded Validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.review_finding import ReviewFindingRead


class FindingEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    evidence_type: str
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    symbol_name: str | None = None
    snippet: str | None = None
    description: str
    source_type: str | None = None
    created_at: datetime


class ValidationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scenario_id: str
    status: str
    exit_code: int | None = None
    stdout_summary: str | None = None
    stderr_summary: str | None = None
    duration_ms: float
    evidence: list[dict[str, Any]] = []
    created_at: datetime


class ValidationScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    scenario_type: str
    description: str
    command: str
    environment: dict[str, Any] = {}
    timeout_seconds: int
    expected_behavior: str
    results: list[ValidationResultRead] = []
    created_at: datetime


class JudgeDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    finding_id: str
    judge_run_id: str
    decision: str
    final_severity: str
    final_confidence: float
    boundary_passed: bool
    factuality_passed: bool
    actionability_passed: bool
    severity_passed: bool
    duplicate_of: str | None = None
    root_cause_id: str | None = None
    verification_summary: str
    rejection_reason: str | None = None
    created_at: datetime


class JudgeRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_job_id: str
    model_name: str
    prompt_version: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    latency_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    decisions: list[JudgeDecisionRead] = []
    created_at: datetime


class VerificationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_job_id: str
    finding_id: str | None = None
    event_type: str
    metadata_json: dict[str, Any] = {}
    created_at: datetime


class VerificationSummaryRead(BaseModel):
    review_job_id: str
    candidate_count: int
    verified_count: int
    rejected_count: int
    needs_validation_count: int
    publishable_count: int
    judge_runs_count: int
    total_judge_tokens: int
    total_judge_cost: float
    rejection_rate: float


class FindingDetailRead(ReviewFindingRead):
    judge_decisions: list[JudgeDecisionRead] = []
    validation_scenarios: list[ValidationScenarioRead] = []
    grounding_evidence: list[FindingEvidenceRead] = []
