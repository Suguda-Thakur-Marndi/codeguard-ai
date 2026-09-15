"""Pydantic schemas for Phase 7 Benchmark Scenarios, Ground Truth, and Results."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ScenarioCategory(StrEnum):
    SECURITY = "SECURITY"
    BUG = "BUG"
    ERROR_HANDLING = "ERROR_HANDLING"
    EDGE_CASES = "EDGE_CASES"
    TEST = "TEST"
    PERFORMANCE = "PERFORMANCE"
    GENERAL_CORRECTNESS = "GENERAL_CORRECTNESS"


class ScenarioType(StrEnum):
    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    AMBIGUOUS = "AMBIGUOUS"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    NO_ISSUE_PR = "NO_ISSUE_PR"
    MULTI_FINDING_PR = "MULTI_FINDING_PR"
    DUPLICATE_ROOT_CAUSE = "DUPLICATE_ROOT_CAUSE"
    STALE_CONTEXT = "STALE_CONTEXT"
    LARGE_DIFF = "LARGE_DIFF"


class FindingClassification(StrEnum):
    TRUE_POSITIVE = "TRUE_POSITIVE"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    FALSE_NEGATIVE = "FALSE_NEGATIVE"


class GroundTruthFinding(BaseModel):
    """Explicit ground-truth specification for an expected (or avoided) finding."""

    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(description="Unique identifier for the ground truth finding (e.g. 'gt-001')")
    category: str = Field(description="Expected finding category (SECURITY, BUG, etc.)")
    severity: str = Field(description="Expected severity (CRITICAL, HIGH, MEDIUM, LOW)")
    file_path: str = Field(description="Relative path of the target file")
    line_start: int = Field(ge=1, description="Start line of expected defect location")
    line_end: int = Field(ge=1, description="End line of expected defect location")
    side: str = Field(default="RIGHT", description="Diff side: LEFT or RIGHT")
    root_cause: str = Field(description="Explanation of the root cause defect")
    keywords: list[str] = Field(default_factory=list, description="Key technical terms for semantic matching")
    remediation_characteristics: list[str] = Field(
        default_factory=list, description="Expected characteristics of an actionable fix"
    )
    is_false_positive_trap: bool = Field(
        default=False,
        description="If True, this finding should NOT be flagged (e.g. caller has guard or intentional pattern)",
    )


class BenchmarkScenario(BaseModel):
    """Complete, reproducible benchmark scenario model."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(description="Unique scenario identifier (e.g. 'py-sec-auth-001')")
    name: str = Field(description="Human-readable title of the benchmark scenario")
    description: str = Field(description="Detailed description of what is being tested")
    version: str = Field(default="1.0.0", description="Semantic version of scenario definition")
    language: str = Field(description="Programming language: python, javascript, typescript")
    scenario_type: ScenarioType = Field(description="Evaluation scenario type")
    category: ScenarioCategory = Field(description="Primary test category")
    difficulty: str = Field(default="MEDIUM", description="EASY, MEDIUM, or HARD")
    tags: list[str] = Field(default_factory=list, description="Descriptive tags for filtering")

    repository_fixture: str = Field(description="Path to repo fixture (e.g. 'fixtures/python_repo')")
    base_commit: str = Field(default="0" * 40, description="Baseline commit SHA")
    test_commit: str = Field(default="1" * 40, description="Test/Head commit SHA")
    pr_number: int = Field(default=1, description="Simulated PR number")
    pr_title: str = Field(description="Simulated PR title")
    pr_description: str = Field(default="", description="Simulated PR description")
    diff: str = Field(description="Raw unified diff for the PR")

    expected_behavior: str = Field(description="Description of correct expected system behavior")
    validation_commands: list[str] = Field(default_factory=list, description="Commands to run for validation")
    ground_truth_findings: list[GroundTruthFinding] = Field(
        default_factory=list, description="List of expected (or avoided) ground truth findings"
    )
    expected_finding_count: int = Field(
        default=1, ge=0, description="Total expected publishable findings (0 for clean/FP scenarios)"
    )

    # Prompt injection testing flag
    contains_prompt_injection: bool = Field(
        default=False, description="Whether the diff contains prompt injection payload"
    )
    injection_payload: str | None = Field(
        default=None, description="Injected command or text that must NOT be executed or obeyed"
    )

    # Optional remediation patch
    reference_patch: str | None = Field(
        default=None, description="Reference patch resolving the issue for patch validation"
    )


class BenchmarkDataset(BaseModel):
    """Container for a versioned dataset of scenarios."""

    model_config = ConfigDict(extra="forbid")

    dataset_version: str = Field(default="v1", description="Dataset version (e.g. 'v1', 'v2')")
    description: str = Field(default="", description="Description of the dataset")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scenarios: list[BenchmarkScenario] = Field(default_factory=list)
