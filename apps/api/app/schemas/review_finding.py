"""API schemas for Phase 3 & 4 ReviewFindings, AgentRuns, and AgentTraces."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_job_id: str
    agent_name: str
    agent_version: str
    model_name: str
    prompt_version: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    latency_ms: float
    retry_count: int
    error_message: str | None = None
    created_at: datetime


class ReviewFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_job_id: str
    agent_run_id: str | None = None
    file_path: str
    line_number: int
    side: str
    start_line: int | None = None
    start_side: str | None = None
    category: str
    severity: str
    original_severity: str | None = None
    final_severity: str | None = None
    title: str
    description: str
    impact: str
    recommendation: str
    confidence: float
    specialist_confidence: float = 1.0
    judge_confidence: float | None = None
    final_confidence: float = 1.0
    evidence: list[dict[str, Any]]
    affected_symbol: str | None = None
    related_files: list[str] = []
    related_symbols: list[str] = []
    agent_name: str
    source_agents: list[str] = []
    duplicate_of: str | None = None
    root_cause_id: str | None = None
    finding_group_id: str | None = None
    status: str
    validation_notes: str | None = None
    created_at: datetime


class AgentTraceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_job_id: str
    agent_run_id: str | None = None
    node_name: str
    agent_name: str
    status: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    model_name: str | None = None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    retry_count: int
    error_message: str | None = None
    created_at: datetime


class AgentUsageBreakdown(BaseModel):
    agent_name: str
    model_name: str
    status: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    latency_ms: float
    retry_count: int


class ReviewUsageRead(BaseModel):
    review_job_id: str
    agent_runs_count: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    total_latency_ms: float
    breakdown_by_agent: list[AgentUsageBreakdown] = []
