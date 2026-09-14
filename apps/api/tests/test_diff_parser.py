"""Unit tests for UnifiedDiffParser."""

from code_intelligence.diff.parser import UnifiedDiffParser
from code_intelligence.models import DiffLineType

SAMPLE_MODIFIED_DIFF = """diff --git a/src/payment.py b/src/payment.py
--- a/src/payment.py
+++ b/src/payment.py
@@ -10,3 +10,6 @@
 class PaymentService:
     def __init__(self):
         self.status = 'READY'
+    def refund(self, payment_id: str) -> bool:
+        # Issue refund
+        return True
"""

SAMPLE_MULTI_FILE_DIFF = """diff --git a/new_module.py b/new_module.py
new file mode 100644
--- /dev/null
+++ b/new_module.py
@@ -0,0 +1,2 @@
+def new_feature():
+    return 42
diff --git a/obsolete.py b/obsolete.py
deleted file mode 100644
--- a/obsolete.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def dead_code():
-    pass
diff --git a/old_name.py b/new_name.py
similarity index 100%
rename from old_name.py
rename to new_name.py
"""

SAMPLE_BINARY_DIFF = """diff --git a/logo.png b/logo.png
new file mode 100644
index 0000000..abcdef1
Binary files /dev/null and b/logo.png differ
"""


def test_parse_modified_file_diff():
    files, diags = UnifiedDiffParser.parse(SAMPLE_MODIFIED_DIFF)
    assert len(files) == 1
    assert len(diags) == 0

    f = files[0]
    assert f.file_path == "src/payment.py"
    assert f.old_path == "src/payment.py"
    assert f.new_path == "src/payment.py"
    assert f.change_type == "modified"
    assert f.is_binary is False

    assert len(f.hunks) == 1
    hunk = f.hunks[0]
    assert hunk.old_start == 10
    assert hunk.new_start == 10

    # Count lines by type
    added = [line for line in hunk.lines if line.type == DiffLineType.ADDED]
    context = [line for line in hunk.lines if line.type == DiffLineType.CONTEXT]
    assert len(added) == 3
    assert len(context) == 3
    assert any("def refund" in line.content for line in added)


def test_parse_multi_file_and_special_changes():
    files, diags = UnifiedDiffParser.parse(SAMPLE_MULTI_FILE_DIFF)
    assert len(files) == 3

    # Added file
    added_file = next(f for f in files if f.change_type == "added")
    assert added_file.file_path == "new_module.py"
    assert added_file.old_path == ""
    assert added_file.new_path == "new_module.py"
    assert len(added_file.hunks) == 1
    assert all(line.type == DiffLineType.ADDED for line in added_file.hunks[0].lines)

    # Deleted file
    deleted_file = next(f for f in files if f.change_type == "deleted")
    assert deleted_file.file_path == "obsolete.py"
    assert deleted_file.old_path == "obsolete.py"
    assert deleted_file.new_path == ""
    assert len(deleted_file.hunks) == 1
    assert all(line.type == DiffLineType.DELETED for line in deleted_file.hunks[0].lines)

    # Renamed file
    renamed_file = next(f for f in files if f.change_type == "renamed")
    assert renamed_file.old_path == "old_name.py"
    assert renamed_file.new_path == "new_name.py"


def test_parse_binary_diff():
    files, diags = UnifiedDiffParser.parse(SAMPLE_BINARY_DIFF)
    assert len(files) == 1
    assert files[0].is_binary is True
    assert files[0].file_path == "logo.png"


def test_parse_empty_or_malformed_diff():
    files, diags = UnifiedDiffParser.parse("")
    assert len(files) == 0
    assert len(diags) == 0

    # Malformed hunk does not raise exception
    malformed = "diff --git a/foo b/foo\n@@ -invalid @@\n+test"
    files2, diags2 = UnifiedDiffParser.parse(malformed)
    assert isinstance(files2, list)
    assert isinstance(diags2, list)
