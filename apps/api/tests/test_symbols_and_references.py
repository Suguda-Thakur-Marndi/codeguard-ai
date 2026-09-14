"""Unit tests for symbol extraction and reference resolution."""

from code_intelligence.languages.python import PythonParser
from code_intelligence.references.resolver import ReferenceResolver

CONTROLLER_CODE = b"""
from services.payment_service import PaymentService

class RefundController:
    def __init__(self):
        self.service = PaymentService()

    def handle(self):
        return self.service.refund("p1", 50.0)
"""

SERVICE_CODE = b"""
from repositories.payment_repository import PaymentRepository

class PaymentService:
    def __init__(self):
        self.repo = PaymentRepository()

    def refund(self, p_id: str, amount: float):
        return self.repo.save(p_id)
"""

REPO_CODE = b"""
class PaymentRepository:
    def save(self, p_id: str):
        return True
"""


def test_cross_file_reference_resolution():
    parser = PythonParser()

    ctrl_tree, _ = parser.parse(CONTROLLER_CODE, "src/api/controller.py")
    svc_tree, _ = parser.parse(SERVICE_CODE, "src/services/payment_service.py")
    repo_tree, _ = parser.parse(REPO_CODE, "src/repositories/payment_repository.py")

    symbols = []
    symbols.extend(parser.extract_symbols(ctrl_tree, CONTROLLER_CODE, "src/api/controller.py"))
    symbols.extend(parser.extract_symbols(svc_tree, SERVICE_CODE, "src/services/payment_service.py"))
    symbols.extend(parser.extract_symbols(repo_tree, REPO_CODE, "src/repositories/payment_repository.py"))

    deps = []
    deps.extend(parser.extract_imports(ctrl_tree, CONTROLLER_CODE, "src/api/controller.py"))
    deps.extend(parser.extract_imports(svc_tree, SERVICE_CODE, "src/services/payment_service.py"))
    deps.extend(parser.extract_imports(repo_tree, REPO_CODE, "src/repositories/payment_repository.py"))

    refs = []
    refs.extend(parser.extract_references(ctrl_tree, CONTROLLER_CODE, "src/api/controller.py"))
    refs.extend(parser.extract_references(svc_tree, SERVICE_CODE, "src/services/payment_service.py"))
    refs.extend(parser.extract_references(repo_tree, REPO_CODE, "src/repositories/payment_repository.py"))

    # Resolve references
    resolved = ReferenceResolver.resolve_references(symbols, refs, deps)

    # refund() call from controller should resolve to payment_service.py
    refund_refs = [r for r in resolved if r.target_symbol == "refund"]
    assert len(refund_refs) >= 1
    assert refund_refs[0].resolved is True
    assert "payment_service.py" in refund_refs[0].target_file

    # save() call from payment_service should resolve to payment_repository.py
    save_refs = [r for r in resolved if r.target_symbol == "save"]
    assert len(save_refs) >= 1
    assert save_refs[0].resolved is True
    assert "payment_repository.py" in save_refs[0].target_file


def test_unresolved_reference_honesty():
    parser = PythonParser()
    unknown_call_code = b"""
def execute():
    external_library_call()
"""
    tree, _ = parser.parse(unknown_call_code, "util.py")
    symbols = parser.extract_symbols(tree, unknown_call_code, "util.py")
    refs = parser.extract_references(tree, unknown_call_code, "util.py")

    resolved = ReferenceResolver.resolve_references(symbols, refs, [])
    assert len(resolved) >= 1
    assert resolved[0].target_symbol == "external_library_call"
    assert resolved[0].resolved is False
    assert resolved[0].target_file is None
