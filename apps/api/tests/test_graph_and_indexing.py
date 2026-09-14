"""Unit tests for Repository Graph and Incremental Indexing."""

from code_intelligence.diff.parser import UnifiedDiffParser
from code_intelligence.engine import CodeIntelligenceEngine
from code_intelligence.source.provider import MemoryRepositorySourceProvider

REPO_V1_FILES = {
    "src/payment.py": b"""class PaymentService:
    def refund(self):
        return True
""",
    "src/legacy.py": b"""def old_func():
    pass
""",
}

PR_DIFF = """diff --git a/src/payment.py b/src/payment.py
--- a/src/payment.py
+++ b/src/payment.py
@@ -1,3 +1,4 @@
 class PaymentService:
     def refund(self):
+        # audited
         return True
diff --git a/src/legacy.py b/src/legacy.py
deleted file mode 100644
--- a/src/legacy.py
+++ /dev/null
@@ -1,2 +0,0 @@
-def old_func():
-    pass
"""

REPO_V2_FILES = {
    "src/payment.py": b"""class PaymentService:
    def refund(self):
        # audited
        return True
""",
}


def test_initial_indexing_and_graph_construction():
    engine = CodeIntelligenceEngine()
    provider = MemoryRepositorySourceProvider(
        files_by_commit={"commit_v1": REPO_V1_FILES}
    )

    result = engine.index_repository("repo-123", "commit_v1", provider)
    assert result.status == "READY"
    assert result.files_processed == 2
    assert len(result.symbols) >= 2
    assert result.graph is not None

    symbol_names = [s.name for s in result.symbols]
    assert "PaymentService" in symbol_names
    assert "PaymentService.refund" in symbol_names
    assert "old_func" in symbol_names


def test_incremental_indexing_with_deletions_and_updates():
    engine = CodeIntelligenceEngine()
    provider_v1 = MemoryRepositorySourceProvider(files_by_commit={"commit_v1": REPO_V1_FILES})
    v1_result = engine.index_repository("repo-123", "commit_v1", provider_v1)

    # Now simulate PR to commit_v2
    diff_files, _ = UnifiedDiffParser.parse(PR_DIFF)
    provider_v2 = MemoryRepositorySourceProvider(files_by_commit={"commit_v2": REPO_V2_FILES})

    incremental_result = engine.index_incremental(
        repository_id="repo-123",
        commit_sha="commit_v2",
        diff_files=diff_files,
        source_provider=provider_v2,
        existing_symbols=v1_result.symbols,
        existing_dependencies=v1_result.dependencies,
        existing_references=v1_result.references,
    )

    assert incremental_result.status == "READY"
    inc_symbols = [s.name for s in incremental_result.symbols]
    # old_func in deleted file src/legacy.py must be removed
    assert "old_func" not in inc_symbols
    # PaymentService must remain
    assert "PaymentService" in inc_symbols
    assert "PaymentService.refund" in inc_symbols


def test_commit_aware_indexing_isolation():
    engine = CodeIntelligenceEngine()
    provider = MemoryRepositorySourceProvider(
        files_by_commit={
            "sha_base": {"main.py": b"def version(): return 1"},
            "sha_head": {"main.py": b"def version(): return 2"},
        }
    )

    base_res = engine.index_repository("repo-1", "sha_base", provider)
    head_res = engine.index_repository("repo-1", "sha_head", provider)

    assert base_res.commit_sha == "sha_base"
    assert head_res.commit_sha == "sha_head"
    assert "return 1" in base_res.symbols[0].source_code
    assert "return 2" in head_res.symbols[0].source_code
