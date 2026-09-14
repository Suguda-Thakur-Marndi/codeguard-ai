"""Unit tests for ChangedLineIndex."""

from code_intelligence.diff.line_index import ChangedLineIndex
from code_intelligence.diff.parser import UnifiedDiffParser
from code_intelligence.models import LineSide

SAMPLE_DIFF = """diff --git a/src/payment.py b/src/payment.py
--- a/src/payment.py
+++ b/src/payment.py
@@ -40,3 +40,4 @@ class PaymentService:
     # context line 40
-    # old deleted line 41
+    # new added line 41
+    # new added line 42
     # context line 43
"""


def test_changed_line_index_left_right_distinction():
    files, _ = UnifiedDiffParser.parse(SAMPLE_DIFF)
    index = ChangedLineIndex(files)

    # RIGHT side contains added line 41, added line 42, and context lines 40, 43
    assert index.is_valid_review_line("src/payment.py", 41, LineSide.RIGHT) is True
    assert index.is_valid_review_line("src/payment.py", 42, LineSide.RIGHT) is True
    assert index.is_valid_review_line("src/payment.py", 40, LineSide.RIGHT) is True
    assert index.is_valid_review_line("src/payment.py", 43, LineSide.RIGHT) is True

    # Out of diff line 999 is not valid
    assert index.is_valid_review_line("src/payment.py", 999, LineSide.RIGHT) is False

    # LEFT side contains deleted line 41 and context lines (40, 42)
    assert index.is_valid_review_line("src/payment.py", 41, LineSide.LEFT) is True
    # Line 43 was added in head, does not exist in base hunk
    assert index.is_valid_review_line("src/payment.py", 43, LineSide.LEFT) is False


def test_get_valid_lines_and_hunk():
    files, _ = UnifiedDiffParser.parse(SAMPLE_DIFF)
    index = ChangedLineIndex(files)

    right_lines = index.get_valid_lines("src/payment.py", LineSide.RIGHT)
    assert 41 in right_lines
    assert 42 in right_lines

    added_only = index.get_added_lines("src/payment.py")
    assert 41 in added_only
    assert 42 in added_only

    hunk = index.get_hunk_for_line("src/payment.py", 41, LineSide.RIGHT)
    assert hunk is not None
    assert hunk.new_start == 40

    non_hunk = index.get_hunk_for_line("src/payment.py", 999, LineSide.RIGHT)
    assert non_hunk is None


def test_deterministic_dictionary_serialization():
    files, _ = UnifiedDiffParser.parse(SAMPLE_DIFF)
    index = ChangedLineIndex(files)
    serialized = index.to_dict()

    assert "src/payment.py" in serialized
    assert "RIGHT" in serialized["src/payment.py"]
    assert "LEFT" in serialized["src/payment.py"]
    assert isinstance(serialized["src/payment.py"]["RIGHT"], list)
