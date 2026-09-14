"""Unit tests for AST semantic expansion and diff-to-AST mapping."""

from code_intelligence.ast.mapper import DiffToASTMapper
from code_intelligence.diff.parser import UnifiedDiffParser

SAMPLE_SOURCE = b"""# Module level comment
import math

class PaymentService:
    def __init__(self):
        self.active = True

    def refund(self, payment_id: str, amount: float) -> bool:
        # line 10
        if amount <= 0:
            raise ValueError('Invalid amount')
        # line 13 (target change)
        audit_log(payment_id, amount)
        return True

    def process(self):
        pass

def top_level_helper():
    return 100
"""

SAMPLE_DIFF = """diff --git a/src/payment_service.py b/src/payment_service.py
--- a/src/payment_service.py
+++ b/src/payment_service.py
@@ -10,2 +10,4 @@ class PaymentService:
         if amount <= 0:
             raise ValueError('Invalid amount')
+        # line 13 (target change)
+        audit_log(payment_id, amount)
"""


def test_diff_to_ast_mapping_method_expansion():
    diff_files, _ = UnifiedDiffParser.parse(SAMPLE_DIFF)
    mapper = DiffToASTMapper()

    mappings, chunks, diags = mapper.map_file_diff_to_ast(
        diff_files[0], SAMPLE_SOURCE, file_path="src/payment_service.py"
    )

    assert len(mappings) >= 1
    m = mappings[0]
    # Smallest useful enclosing semantic entity must be the method PaymentService.refund
    assert m.symbol_name == "PaymentService.refund"
    assert m.start_line <= 13 <= m.end_line
    assert m.chunk.node_type == "function_definition"
    assert "def refund" in m.chunk.source_code


def test_diff_to_ast_mapping_class_expansion():
    class_source = b"""# Module
class PaymentService:
    SERVICE_NAME = 'PAYMENT_CORE'

    def refund(self):
        pass
"""
    class_diff = """diff --git a/src/payment_service.py b/src/payment_service.py
--- a/src/payment_service.py
+++ b/src/payment_service.py
@@ -2,1 +2,2 @@ class PaymentService:
 class PaymentService:
+    SERVICE_NAME = 'PAYMENT_CORE'
"""
    diff_files, _ = UnifiedDiffParser.parse(class_diff)
    mapper = DiffToASTMapper()

    mappings, chunks, _ = mapper.map_file_diff_to_ast(
        diff_files[0], class_source, file_path="src/payment_service.py"
    )

    assert len(mappings) >= 1
    assert mappings[0].symbol_name == "PaymentService"
    assert mappings[0].chunk.node_type == "class_definition"


def test_diff_to_ast_mapping_standalone_function():
    func_diff = """diff --git a/src/payment_service.py b/src/payment_service.py
--- a/src/payment_service.py
+++ b/src/payment_service.py
@@ -19,2 +19,3 @@ def top_level_helper():
 def top_level_helper():
+    x = 1
     return 100
"""
    diff_files, _ = UnifiedDiffParser.parse(func_diff)
    mapper = DiffToASTMapper()

    mappings, chunks, _ = mapper.map_file_diff_to_ast(
        diff_files[0], SAMPLE_SOURCE, file_path="src/payment_service.py"
    )

    assert len(mappings) >= 1
    assert mappings[0].symbol_name == "top_level_helper"
    assert mappings[0].chunk.node_type == "function_definition"
