"""Tests for deterministic FindingValidator, line boundary enforcement, and anti-hallucination rules."""

import pytest

from app.agents.orchestrator.validator import FindingValidator
from app.agents.schemas.finding import (
    EvidenceItem,
    EvidenceType,
    FindingCategory,
    FindingSeverity,
    FindingStatus,
    ReviewFinding,
)


def create_sample_finding(
    file_path: str = "src/payment.py",
    line_number: int = 100,
    side: str = "RIGHT",
    confidence: float = 0.90,
    evidence: list[EvidenceItem] | None = None,
) -> ReviewFinding:
    return ReviewFinding(
        file_path=file_path,
        line_number=line_number,
        side=side,
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Insecure direct object reference",
        description="User-supplied ID is used without authorization verification.",
        impact="Unauthorized callers can modify external accounts.",
        recommendation="Verify caller identity and ownership before processing operation.",
        confidence=confidence,
        evidence=evidence
        if evidence is not None
        else [
            EvidenceItem(
                type=EvidenceType.CODE,
                file=file_path,
                line_start=line_number,
                line_end=line_number + 2,
                description="Unchecked ID reference",
            )
        ],
        agent_name="security",
    )


def test_validator_accepts_valid_finding():
    """Validator should mark finding as VALID when file, line, side, and evidence are strictly valid."""
    finding = create_sample_finding(line_number=101)
    changed_files = ["src/payment.py", "src/auth.py"]
    changed_lines = {"src/payment.py": {"RIGHT": [100, 101, 105], "LEFT": [98]}}

    valid, invalid = FindingValidator.validate_findings(
        findings=[finding],
        changed_files=changed_files,
        changed_lines_by_file=changed_lines,
    )

    assert len(valid) == 1
    assert len(invalid) == 0
    assert valid[0].status == FindingStatus.VALID
    assert "Verified" in valid[0].validation_notes


def test_validator_rejects_hallucinated_line_999():
    """CRITICAL REQUIREMENT: Line 999 must be REJECTED when valid lines are 100, 101, 105."""
    hallucinated_finding = create_sample_finding(line_number=999)
    changed_files = ["src/payment.py"]
    changed_lines = {"src/payment.py": {"RIGHT": [100, 101, 105], "LEFT": []}}

    valid, invalid = FindingValidator.validate_findings(
        findings=[hallucinated_finding],
        changed_files=changed_files,
        changed_lines_by_file=changed_lines,
    )

    assert len(valid) == 0
    assert len(invalid) == 1
    assert invalid[0].status == FindingStatus.INVALID
    assert "Hallucinated line 999" in invalid[0].validation_notes


def test_validator_rejects_nonexistent_file():
    """Validator should reject finding if LLM hallucinates a file outside the PR diff."""
    finding = create_sample_finding(file_path="src/hallucinated_service.py", line_number=50)
    changed_files = ["src/payment.py"]
    changed_lines = {"src/payment.py": {"RIGHT": [100, 101, 105]}}

    valid, invalid = FindingValidator.validate_findings(
        findings=[finding],
        changed_files=changed_files,
        changed_lines_by_file=changed_lines,
    )

    assert len(valid) == 0
    assert len(invalid) == 1
    assert invalid[0].status == FindingStatus.INVALID
    assert "does not exist among changed files" in invalid[0].validation_notes


def test_validator_side_autocorrection():
    """Validator should auto-correct side if line exists on LEFT side instead of RIGHT."""
    finding = create_sample_finding(line_number=98, side="RIGHT")
    changed_files = ["src/payment.py"]
    changed_lines = {"src/payment.py": {"RIGHT": [100, 101, 105], "LEFT": [98]}}

    valid, invalid = FindingValidator.validate_findings(
        findings=[finding],
        changed_files=changed_files,
        changed_lines_by_file=changed_lines,
    )

    assert len(valid) == 1
    assert valid[0].status == FindingStatus.VALID
    assert valid[0].side == "LEFT"


def test_validator_rejects_missing_evidence():
    """Validator should reject candidate finding if evidence items are empty or invalid."""
    finding = create_sample_finding(evidence=[])
    changed_files = ["src/payment.py"]
    changed_lines = {"src/payment.py": {"RIGHT": [100]}}

    valid, invalid = FindingValidator.validate_findings(
        findings=[finding],
        changed_files=changed_files,
        changed_lines_by_file=changed_lines,
    )

    assert len(valid) == 0
    assert len(invalid) == 1
    assert "Missing evidence" in invalid[0].validation_notes


def test_validator_rejects_invalid_confidence():
    """ReviewFinding Pydantic schema must reject confidence outside [0.0, 1.0]."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        create_sample_finding(confidence=1.45)
    with pytest.raises(ValidationError):
        create_sample_finding(confidence=-0.1)
