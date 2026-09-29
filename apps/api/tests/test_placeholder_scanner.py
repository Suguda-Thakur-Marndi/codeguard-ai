"""Regression test suite for zero-placeholder scanner.

Protects against false positives in the placeholder scanner while ensuring genuine
unfinished implementation stubs (raise NotImplementedError, TODO, FIXME) are strictly caught.

Covers:
 1. A genuine `raise NotImplementedError` production stub is detected.
 2. A harmless textual mention is not treated as an implementation stub.
 3. A scanner regular expression does not trigger a false positive.
 4. Documentation describing the audit does not trigger a false positive.
 5. Existing real placeholders, if any, remain detectable.
"""

import sys
from pathlib import Path

# Add project root to path to import scan_file_for_placeholders from verify_phase10
root_dir = Path(__file__).resolve().parent.parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from verify_phase10 import scan_file_for_placeholders  # noqa: E402


def test_genuine_raise_not_implemented_error_detected():
    """Verify that a genuine raise NotImplementedError in production Python code is caught."""
    code_snippet = '''
def process_incoming_event(event_data: dict) -> None:
    # Production implementation pending
    raise NotImplementedError("process_incoming_event not yet implemented")
'''
    issues = scan_file_for_placeholders("app/services/event_processor.py", code_snippet)
    assert len(issues) == 1
    line_num, desc = issues[0]
    assert line_num == 4
    assert "NotImplementedError" in desc


def test_genuine_raise_not_implemented_bare_detected():
    """Verify that a bare raise NotImplementedError (without arguments) is caught."""
    code_snippet = '''
class BaseWorker:
    def execute(self) -> None:
        raise NotImplementedError
'''
    issues = scan_file_for_placeholders("app/workers/base.py", code_snippet)
    assert len(issues) == 1
    line_num, desc = issues[0]
    assert line_num == 4
    assert "NotImplementedError" in desc


def test_harmless_textual_mention_not_flagged():
    """Verify that markdown report text mentioning NotImplementedError is not treated as a stub."""
    markdown_report_snippet = '''
## Acceptance Report Summary
- Zero unhandled production placeholders (`raise NotImplementedError`).
- All 30 scenarios passed.
'''
    issues = scan_file_for_placeholders("docs/acceptance/report.py", markdown_report_snippet)
    assert len(issues) == 0, f"Expected 0 issues, got: {issues}"


def test_scanner_regular_expression_not_flagged():
    """Verify that regular expressions searching for raise NotImplementedError do not trigger false positives."""
    scanner_pattern_snippet = '''
import re

def audit_files():
    placeholder_pat = re.compile(r"raise\\s+NotImplementedError")
    return placeholder_pat
'''
    issues = scan_file_for_placeholders("scripts/run_acceptance_suite.py", scanner_pattern_snippet)
    assert len(issues) == 0, f"Expected 0 issues, got: {issues}"


def test_documentation_and_docstrings_not_flagged():
    """Verify that docstrings describing the audit or referencing NotImplementedError do not trigger false positives."""
    docstring_snippet = '''
def run_audit_ph(self) -> None:
    """AUDIT-PH: Zero-placeholder audit in production code to ensure no raise NotImplementedError."""
    pass
'''
    issues = scan_file_for_placeholders("scripts/audit_tool.py", docstring_snippet)
    assert len(issues) == 0, f"Expected 0 issues, got: {issues}"


def test_todo_and_fixme_placeholders_detected():
    """Verify that unresolved TODO and FIXME comments remain detectable across code."""
    todo_snippet = '''
def dispatch_job(job_id: str):
    # TODO: Add Redis distributed lock
    pass
'''
    issues = scan_file_for_placeholders("app/services/dispatcher.py", todo_snippet)
    assert len(issues) == 1
    assert "Unresolved TODO" in issues[0][1]

    fixme_snippet = '''
def calculate_cost(tokens: int) -> float:
    # FIXME: Update pricing model for Gemini 2.5
    return 0.0
'''
    issues_fixme = scan_file_for_placeholders("app/services/pricing.py", fixme_snippet)
    assert len(issues_fixme) == 1
    assert "Unresolved FIXME" in issues_fixme[0][1]
