"""Unit tests for ContextRanker and token budgeting."""

from code_intelligence.context.ranker import ContextRanker
from code_intelligence.graph.builder import RepositoryGraph
from code_intelligence.models import ASTChunk, RankedContextItem, Symbol, SymbolKind


def test_context_ranking_weights():
    ranker = ContextRanker()

    items = [
        RankedContextItem(
            entity_type="DEPENDENCY",
            identifier="TwoHopService",
            file_path="src/two_hop.py",
            relevance_score=ranker.WEIGHT_TWO_HOP,
            reason="two hop",
        ),
        RankedContextItem(
            entity_type="CALLER",
            identifier="RefundController",
            file_path="src/controller.py",
            relevance_score=ranker.WEIGHT_DIRECT_CALLER,
            reason="direct caller",
        ),
        RankedContextItem(
            entity_type="CHUNK",
            identifier="PaymentService.refund",
            file_path="src/payment.py",
            relevance_score=ranker.WEIGHT_CHANGED_FILE,
            reason="changed chunk",
        ),
    ]

    budgeted = ranker.rank_and_budget(items, max_files=10, max_symbols=10)
    assert len(budgeted) == 3
    # First item must be changed chunk (highest weight 1.0)
    assert budgeted[0].identifier == "PaymentService.refund"
    # Second item must be direct caller (0.85)
    assert budgeted[1].identifier == "RefundController"
    # Third item must be two hop (0.50)
    assert budgeted[2].identifier == "TwoHopService"


def test_context_budget_capping():
    ranker = ContextRanker()

    # Create 10 items in 10 different files with character payloads
    items = [
        RankedContextItem(
            entity_type="SYMBOL",
            identifier=f"Symbol_{i}",
            file_path=f"src/file_{i}.py",
            relevance_score=1.0 - (i * 0.05),
            reason="test",
            char_count=500,
        )
        for i in range(10)
    ]

    # Budget restricted to max 3 files
    file_budgeted = ranker.rank_and_budget(items, max_files=3, max_symbols=10, max_characters=10000)
    assert len(file_budgeted) == 3
    unique_files = {item.file_path for item in file_budgeted}
    assert len(unique_files) == 3

    # Budget restricted to character limit (e.g. 1200 chars -> max 2 items of 500 chars)
    char_budgeted = ranker.rank_and_budget(items, max_files=10, max_symbols=10, max_characters=1200)
    assert len(char_budgeted) == 2


def test_build_relevant_context_assembly():
    ranker = ContextRanker()
    chunk = ASTChunk(
        id="chunk1",
        file_path="src/payment.py",
        language="python",
        node_type="function_definition",
        symbol_name="PaymentService.refund",
        start_line=10,
        end_line=20,
        start_byte=100,
        end_byte=300,
        source_code="def refund(): pass",
        parent_symbol="PaymentService",
        signature="def refund() -> bool",
    )

    graph = RepositoryGraph("repo1", "sha1")
    graph.add_node("file::src/payment.py", "File", "src/payment.py", "src/payment.py")
    graph.add_node("file::src/controller.py", "File", "src/controller.py", "src/controller.py")
    graph.add_node("file::src/repo.py", "File", "src/repo.py", "src/repo.py")

    graph.add_node("src/payment.py::PaymentService.refund", "METHOD", "PaymentService.refund", "src/payment.py")
    graph.add_node("src/controller.py::RefundController", "CLASS", "RefundController", "src/controller.py")

    # Caller edge
    graph.add_edge("src/controller.py::RefundController", "src/payment.py::PaymentService.refund", "CALLS")
    # Dependency edge
    graph.add_edge("file::src/payment.py", "file::src/repo.py", "IMPORTS")

    symbols = [
        Symbol(
            symbol_id="s1",
            name="PaymentService.refund",
            kind=SymbolKind.METHOD,
            file_path="src/payment.py",
            start_line=10,
            end_line=20,
            language="python",
            signature="def refund() -> bool",
        )
    ]

    context = ranker.build_relevant_context(
        repository_id="repo1",
        commit_sha="sha1",
        changed_file="src/payment.py",
        changed_symbol="PaymentService.refund",
        changed_chunk=chunk,
        graph=graph,
        symbols=symbols,
    )

    assert context.changed_file == "src/payment.py"
    assert context.changed_symbol == "PaymentService.refund"
    assert context.parent_entity == "PaymentService"
    assert any("controller.py" in caller for caller in context.direct_callers)
    assert any("repo.py" in dep for dep in context.direct_dependencies)
    assert len(context.ranked_items) >= 1
