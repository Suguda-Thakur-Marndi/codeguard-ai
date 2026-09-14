"""Pydantic schemas for Adversarial Judge decisions and validation outputs."""

import enum

from pydantic import BaseModel, Field

from app.agents.schemas.finding import (
    EvidenceItem,
    FindingSeverity,
    FindingStatus,
)


class JudgeDecisionType(enum.StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    NEEDS_EXECUTION_VALIDATION = "NEEDS_EXECUTION_VALIDATION"


class JudgeDecision(BaseModel):
    """Structured decision output from the Adversarial Judge for a candidate finding."""

    finding_id: str = Field(..., description="ID of the candidate finding evaluated")
    decision: JudgeDecisionType = Field(
        ..., description="ACCEPT (verified), REJECT (invalid/mitigated/vague), or NEEDS_EXECUTION_VALIDATION"
    )
    final_severity: FindingSeverity = Field(
        ..., description="Audited severity after judge evaluation (may downgrade from specialist)"
    )
    judge_confidence: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Confidence score from the judge evaluation"
    )
    final_confidence: float = Field(
        default=0.9, ge=0.0, le=1.0, description="Computed final confidence score"
    )

    boundary_passed: bool = Field(
        default=True, description="True if line number and diff hunk boundaries are valid"
    )
    factuality_passed: bool = Field(
        default=True, description="True if claimed code exists and is not mitigated by existing guards"
    )
    actionability_passed: bool = Field(
        default=True, description="True if finding provides concrete, non-vague remediation"
    )
    severity_passed: bool = Field(
        default=True, description="True if specialist severity was appropriate or normalized"
    )

    duplicate_of: str | None = Field(
        default=None, description="Finding ID of canonical duplicate finding if identified"
    )
    root_cause_id: str | None = Field(
        default=None, description="Shared root cause ID if grouped with other findings"
    )

    rejection_reason: str | None = Field(
        default=None, description="Concise explanation if rejected (e.g. INVALID_DIFF_LOCATION, FACTUALITY_FAILURE, VAGUE_COMMENT)"
    )
    verification_summary: str = Field(
        ..., description="Auditable reasoning explaining why each gate passed or failed"
    )
    evidence: list[EvidenceItem] = Field(
        default_factory=list, description="Grounding evidence verifying or disproving the finding"
    )


class FinalFindingDecision(BaseModel):
    """Final decision produced for a candidate finding after judge and execution validation."""

    finding_id: str
    status: FindingStatus  # REJECTED, VALIDATED, EXECUTION_VERIFIED, PUBLISHABLE
    final_severity: FindingSeverity
    final_confidence: float
    rejection_reason: str | None = None
    verification_summary: str = ""
    evidence_chain: list[EvidenceItem] = Field(default_factory=list)
    source_agents: list[str] = Field(default_factory=list)
    root_cause_id: str | None = None
    duplicate_of: str | None = None


class BatchJudgeOutput(BaseModel):
    """Structured response schema when evaluating candidate findings in batch."""

    decisions: list[JudgeDecision] = Field(
        default_factory=list, description="List of judge decisions for evaluated findings"
    )
    summary: str = Field(
        default="Adversarial evaluation completed.",
        description="High-level summary of batch evaluation",
    )
