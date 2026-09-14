"""Unit tests for Tree-sitter Language Parsers (Python, JS, TS)."""

from code_intelligence.languages.javascript import JavaScriptParser
from code_intelligence.languages.python import PythonParser
from code_intelligence.languages.typescript import TypeScriptParser
from code_intelligence.models import SymbolKind


def test_python_parser_entities():
    parser = PythonParser()
    code = b"""
from auth import verify
import os

class PaymentGateway:
    def __init__(self, key: str):
        self.key = key

    def refund(self, payment_id: str, amount: float) -> bool:
        verify(payment_id)
        return True

def standalone_helper():
    pass
"""
    tree, diags = parser.parse(code, "test.py")
    assert tree is not None
    assert len(diags) == 0

    symbols = parser.extract_symbols(tree, code, "test.py")
    names = {s.name: s for s in symbols}

    assert "PaymentGateway" in names
    assert names["PaymentGateway"].kind == SymbolKind.CLASS

    assert "PaymentGateway.refund" in names
    assert names["PaymentGateway.refund"].kind == SymbolKind.METHOD
    assert "payment_id: str" in names["PaymentGateway.refund"].signature
    assert names["PaymentGateway.refund"].return_type == "bool"

    assert "standalone_helper" in names
    assert names["standalone_helper"].kind == SymbolKind.FUNCTION

    # Imports
    deps = parser.extract_imports(tree, code, "test.py")
    assert any("auth.py" in d.target_file for d in deps)

    # References
    refs = parser.extract_references(tree, code, "test.py")
    assert any(r.target_symbol == "verify" for r in refs)


def test_javascript_parser_entities():
    parser = JavaScriptParser()
    code = b"""
const { db } = require('./db');

class OrderService {
    cancel(orderId) {
        db.delete(orderId);
        return true;
    }
}

function computeTax(amount) {
    return amount * 0.1;
}

const formatCurrency = (val) => '$' + val;
"""
    tree, diags = parser.parse(code, "order.js")
    assert tree is not None

    symbols = parser.extract_symbols(tree, code, "order.js")
    names = {s.name: s for s in symbols}

    assert "OrderService" in names
    assert "OrderService.cancel" in names
    assert "computeTax" in names
    assert "formatCurrency" in names

    deps = parser.extract_imports(tree, code, "order.js")
    assert any("db.js" in d.target_file for d in deps)

    refs = parser.extract_references(tree, code, "order.js")
    assert any(r.target_symbol == "delete" for r in refs)


def test_typescript_parser_entities():
    parser = TypeScriptParser()
    code = b"""
import { Config } from './config';

export interface IPaymentRecord {
    id: string;
    amount: number;
}

export type Status = 'NEW' | 'PROCESSED';

export class PaymentProcessor implements IProcessor {
    process(record: IPaymentRecord): boolean {
        return true;
    }
}
"""
    tree, diags = parser.parse(code, "processor.ts")
    assert tree is not None

    symbols = parser.extract_symbols(tree, code, "processor.ts")
    names = {s.name: s for s in symbols}

    assert "IPaymentRecord" in names
    assert names["IPaymentRecord"].kind == SymbolKind.INTERFACE

    assert "Status" in names
    assert names["Status"].kind == SymbolKind.TYPE

    assert "PaymentProcessor" in names
    assert names["PaymentProcessor"].kind == SymbolKind.CLASS

    assert "PaymentProcessor.process" in names
    assert names["PaymentProcessor.process"].kind == SymbolKind.METHOD

    refs = parser.extract_references(tree, code, "processor.ts")
    assert any(r.target_symbol == "IProcessor" for r in refs)


def test_parser_syntax_error_resilience():
    parser = PythonParser()
    broken_code = b"""
def valid_function():
    return 1

def broken_function(
    # missing paren and syntax
class NextClass:
    pass
"""
    tree, diags = parser.parse(broken_code, "broken.py")
    assert tree is not None
    assert len(diags) >= 1
    assert any("syntax error" in d.message.lower() for d in diags)

    # Valid functions can still be extracted despite syntax errors in other functions
    symbols = parser.extract_symbols(tree, broken_code, "broken.py")
    assert any(s.name == "valid_function" for s in symbols)
