"""Tests for ValidationPolicy engine and StaticAnalyzer adapters (Phase 4)."""

import pytest

from app.agents.schemas.finding import FindingCategory, FindingSeverity
from app.agents.validation.policy import ExecutionDecision, ValidationPolicy
from app.agents.validation.static import RuffAnalyzer, StaticAnalysisManager


def test_validation_policy_advisory():
    """Advisory severity should never require execution."""
    decision = ValidationPolicy.evaluate(
        category=FindingCategory.BUG,
        severity=FindingSeverity.ADVISORY,
        confidence=0.9,
    )
    assert decision == ExecutionDecision.NO_EXECUTION


def test_validation_policy_high_severity_bug_with_tests():
    """High severity bug with test suite should trigger sandbox execution."""
    decision = ValidationPolicy.evaluate(
        category=FindingCategory.BUG,
        severity=FindingSeverity.HIGH,
        confidence=0.85,
        has_test_suite=True,
        is_safe_sandbox_target=True,
    )
    assert decision == ExecutionDecision.EXECUTE


def test_validation_policy_bug_without_tests():
    """Bug without test suite should fall back to STATIC_ONLY."""
    decision = ValidationPolicy.evaluate(
        category=FindingCategory.BUG,
        severity=FindingSeverity.HIGH,
        confidence=0.85,
        has_test_suite=False,
    )
    assert decision == ExecutionDecision.STATIC_ONLY


def test_validation_policy_contract_and_test_coverage():
    """Contract or test coverage findings should use STATIC_ONLY."""
    decision = ValidationPolicy.evaluate(
        category=FindingCategory.CONTRACT,
        severity=FindingSeverity.HIGH,
        confidence=0.85,
    )
    assert decision == ExecutionDecision.STATIC_ONLY


def test_validation_policy_critical_security():
    """Critical security finding with safe sandbox target should execute."""
    decision = ValidationPolicy.evaluate(
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.CRITICAL,
        confidence=0.92,
        has_test_suite=True,
        is_safe_sandbox_target=True,
    )
    assert decision == ExecutionDecision.EXECUTE


def test_static_analysis_manager_initialization():
    """StaticAnalysisManager loads enabled adapters and handles missing tools gracefully."""
    manager = StaticAnalysisManager()
    assert "ruff" in manager.analyzers
    assert "eslint" in manager.analyzers
    assert "semgrep" in manager.analyzers


@pytest.mark.asyncio
async def test_ruff_analyzer_unavailable_handling():
    """If ruff is unavailable or file is checked, it safely returns a normalized result."""
    analyzer = RuffAnalyzer()
    res = await analyzer.analyze_file(".", "non_existent.py")
    assert res.tool == "ruff"
    assert isinstance(res.passed, bool)
