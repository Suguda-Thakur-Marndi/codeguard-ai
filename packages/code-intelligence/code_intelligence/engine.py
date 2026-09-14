"""Central orchestrator for repository indexing, diff analysis, and context extraction."""

import time

from code_intelligence.ast.mapper import DiffLineMapping, DiffToASTMapper
from code_intelligence.context.ranker import ContextRanker
from code_intelligence.diff.line_index import ChangedLineIndex
from code_intelligence.diff.parser import UnifiedDiffParser
from code_intelligence.filter.file_filter import FileFilter
from code_intelligence.graph.builder import RepositoryGraph, RepositoryGraphBuilder
from code_intelligence.languages.registry import (
    LanguageParserRegistry,
    default_registry,
)
from code_intelligence.models import (
    ASTChunk,
    DiagnosticSeverity,
    DiagnosticStage,
    DiffFile,
    FileDependency,
    ParserDiagnostic,
    RelevantContext,
    Symbol,
    SymbolReference,
)
from code_intelligence.references.resolver import ReferenceResolver
from code_intelligence.source.provider import RepositorySourceProvider


class IndexingResult:
    """Outcome of full or incremental repository indexing."""

    def __init__(self, repository_id: str, commit_sha: str):
        self.repository_id = repository_id
        self.commit_sha = commit_sha
        self.status: str = "READY"
        self.files_processed: int = 0
        self.files_failed: int = 0
        self.symbols: list[Symbol] = []
        self.dependencies: list[FileDependency] = []
        self.references: list[SymbolReference] = []
        self.graph: RepositoryGraph | None = None
        self.diagnostics: list[ParserDiagnostic] = []
        self.metrics: dict[str, float] = {}

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == DiagnosticSeverity.ERROR)


class PRAnalysisResult:
    """Outcome of PR diff parsing, AST mapping, and code intelligence enrichment."""

    def __init__(self):
        self.diff_files: list[DiffFile] = []
        self.line_index: ChangedLineIndex | None = None
        self.changed_line_mappings: list[DiffLineMapping] = []
        self.ast_chunks: list[ASTChunk] = []
        self.context_by_symbol: dict[str, RelevantContext] = {}
        self.diagnostics: list[ParserDiagnostic] = []
        self.metrics: dict[str, float] = {}


class CodeIntelligenceEngine:
    """Master engine orchestrating static AST analysis, repository graph, and context retrieval."""

    def __init__(
        self,
        registry: LanguageParserRegistry | None = None,
        file_filter: FileFilter | None = None,
        context_ranker: ContextRanker | None = None,
    ):
        self.registry = registry or default_registry
        self.file_filter = file_filter or FileFilter()
        self.context_ranker = context_ranker or ContextRanker()
        self.diff_mapper = DiffToASTMapper(self.registry)

    def index_repository(
        self,
        repository_id: str,
        commit_sha: str,
        source_provider: RepositorySourceProvider,
    ) -> IndexingResult:
        """Perform full repository indexing at commit_sha."""
        t_start = time.perf_counter()
        result = IndexingResult(repository_id, commit_sha)

        all_files = source_provider.get_files(commit_sha)

        ast_parse_ms = 0.0
        symbol_extract_ms = 0.0

        for file_path, content in all_files.items():
            if not self.file_filter.is_indexable_file(file_path):
                continue

            if self.file_filter.is_binary(content):
                result.diagnostics.append(
                    ParserDiagnostic(
                        file_path=file_path,
                        stage=DiagnosticStage.FILE_READ,
                        error_type="SKIPPED_BINARY",
                        message="File contains binary content; skipped Tree-sitter parsing.",
                        severity=DiagnosticSeverity.INFO,
                    )
                )
                continue

            ok, limit_err = self.file_filter.check_file_limits(file_path, content)
            if not ok:
                result.diagnostics.append(
                    ParserDiagnostic(
                        file_path=file_path,
                        stage=DiagnosticStage.FILE_READ,
                        error_type="SKIPPED_LARGE_FILE",
                        message=limit_err or "File exceeded size or line limits",
                        severity=DiagnosticSeverity.WARNING,
                    )
                )
                continue

            parser = self.registry.get_parser(file_path)
            if not parser:
                continue

            # Parse AST
            t0 = time.perf_counter()
            tree, diags = parser.parse(content, file_path=file_path)
            ast_parse_ms += (time.perf_counter() - t0) * 1000
            result.diagnostics.extend(diags)

            if not tree:
                result.files_failed += 1
                continue

            # Extract Symbols, Imports, References
            t1 = time.perf_counter()
            try:
                symbols = parser.extract_symbols(tree, content, file_path)
                deps = parser.extract_imports(tree, content, file_path)
                refs = parser.extract_references(tree, content, file_path)

                result.symbols.extend(symbols)
                result.dependencies.extend(deps)
                result.references.extend(refs)
                result.files_processed += 1
            except Exception as exc:  # noqa: BLE001
                result.files_failed += 1
                result.diagnostics.append(
                    ParserDiagnostic(
                        file_path=file_path,
                        stage=DiagnosticStage.SYMBOL_EXTRACTION,
                        error_type=exc.__class__.__name__,
                        message=f"Error extracting symbols: {exc!s}",
                        severity=DiagnosticSeverity.ERROR,
                    )
                )
            symbol_extract_ms += (time.perf_counter() - t1) * 1000

        # Resolve References
        t_ref = time.perf_counter()
        result.references = ReferenceResolver.resolve_references(
            result.symbols, result.references, result.dependencies
        )
        ref_resolution_ms = (time.perf_counter() - t_ref) * 1000

        # Build Graph
        t_graph = time.perf_counter()
        result.graph = RepositoryGraphBuilder.build_graph(
            repository_id=repository_id,
            commit_sha=commit_sha,
            symbols=result.symbols,
            references=result.references,
            dependencies=result.dependencies,
        )
        graph_update_ms = (time.perf_counter() - t_graph) * 1000

        total_ms = (time.perf_counter() - t_start) * 1000
        result.metrics = {
            "ast_parse_ms": round(ast_parse_ms, 2),
            "symbol_extraction_ms": round(symbol_extract_ms, 2),
            "reference_resolution_ms": round(ref_resolution_ms, 2),
            "graph_update_ms": round(graph_update_ms, 2),
            "total_indexing_ms": round(total_ms, 2),
        }

        if result.files_failed > 0 and result.files_processed > 0:
            result.status = "PARTIAL"
        elif result.files_failed > 0 and result.files_processed == 0:
            result.status = "FAILED"
        else:
            result.status = "READY"

        return result

    def index_incremental(
        self,
        repository_id: str,
        commit_sha: str,
        diff_files: list[DiffFile],
        source_provider: RepositorySourceProvider,
        existing_symbols: list[Symbol],
        existing_dependencies: list[FileDependency],
        existing_references: list[SymbolReference],
    ) -> IndexingResult:
        """
        Incrementally update repository index for changed files in a PR
        without full repository re-parsing.
        """
        t_start = time.perf_counter()
        result = IndexingResult(repository_id, commit_sha)

        affected_paths: set[str] = set()
        deleted_paths: set[str] = set()
        renamed_pairs: dict[str, str] = {}  # old -> new

        for df in diff_files:
            if df.change_type == "deleted":
                deleted_paths.add(df.file_path)
            elif df.change_type == "renamed":
                renamed_pairs[df.old_path] = df.new_path
                affected_paths.add(df.new_path)
            else:
                affected_paths.add(df.file_path)

        # 1. Retain unchanged symbols, updating renames
        retained_symbols: list[Symbol] = []
        for sym in existing_symbols:
            if sym.file_path in deleted_paths or sym.file_path in affected_paths:
                continue
            if sym.file_path in renamed_pairs:
                sym.file_path = renamed_pairs[sym.file_path]
            retained_symbols.append(sym)

        # 2. Retain unchanged dependencies
        retained_deps: list[FileDependency] = []
        for dep in existing_dependencies:
            if dep.source_file in deleted_paths or dep.source_file in affected_paths:
                continue
            if dep.source_file in renamed_pairs:
                dep.source_file = renamed_pairs[dep.source_file]
            if dep.target_file in renamed_pairs:
                dep.target_file = renamed_pairs[dep.target_file]
            retained_deps.append(dep)

        # 3. Retain unchanged references
        retained_refs: list[SymbolReference] = []
        for ref in existing_references:
            if ref.source_file in deleted_paths or ref.source_file in affected_paths:
                continue
            if ref.source_file in renamed_pairs:
                ref.source_file = renamed_pairs[ref.source_file]
            if ref.target_file and ref.target_file in renamed_pairs:
                ref.target_file = renamed_pairs[ref.target_file]
            retained_refs.append(ref)

        # 4. Parse only changed files from source_provider
        new_symbols: list[Symbol] = []
        new_deps: list[FileDependency] = []
        new_refs: list[SymbolReference] = []

        for path in affected_paths:
            content = source_provider.get_file(path, commit_sha)
            if not content:
                continue
            if not self.file_filter.is_indexable_file(path) or self.file_filter.is_binary(content):
                continue
            parser = self.registry.get_parser(path)
            if not parser:
                continue

            tree, diags = parser.parse(content, file_path=path)
            result.diagnostics.extend(diags)
            if tree:
                new_symbols.extend(parser.extract_symbols(tree, content, path))
                new_deps.extend(parser.extract_imports(tree, content, path))
                new_refs.extend(parser.extract_references(tree, content, path))
                result.files_processed += 1
            else:
                result.files_failed += 1

        all_symbols = retained_symbols + new_symbols
        all_deps = retained_deps + new_deps
        all_refs = ReferenceResolver.resolve_references(all_symbols, retained_refs + new_refs, all_deps)

        result.symbols = all_symbols
        result.dependencies = all_deps
        result.references = all_refs
        result.graph = RepositoryGraphBuilder.build_graph(
            repository_id, commit_sha, all_symbols, all_refs, all_deps
        )

        total_ms = (time.perf_counter() - t_start) * 1000
        result.metrics["incremental_indexing_ms"] = round(total_ms, 2)
        result.status = "READY"
        return result

    def analyze_pull_request(
        self,
        raw_diff: str,
        source_provider: RepositorySourceProvider,
        head_sha: str,
        repository_id: str,
        repository_graph: RepositoryGraph | None = None,
        all_symbols: list[Symbol] | None = None,
    ) -> PRAnalysisResult:
        """
        Execute full Phase 2 PR review pipeline:
        diff parse -> line index -> changed files AST mapping -> context retrieval.
        """
        t_start = time.perf_counter()
        result = PRAnalysisResult()

        # 1. Parse unified diff
        t_diff = time.perf_counter()
        diff_files, diff_diags = UnifiedDiffParser.parse(raw_diff)
        result.diff_files = diff_files
        result.diagnostics.extend(diff_diags)
        result.metrics["diff_parse_ms"] = round((time.perf_counter() - t_diff) * 1000, 2)

        # 2. Build changed line index
        result.line_index = ChangedLineIndex(diff_files)

        # 3. Map changed lines to AST chunks
        t_ast = time.perf_counter()
        for df in diff_files:
            if df.change_type == "deleted" or df.is_binary:
                continue
            source_content = source_provider.get_file(df.file_path, head_sha)
            if not source_content:
                continue

            mappings, chunks, map_diags = self.diff_mapper.map_file_diff_to_ast(
                df, source_content, file_path=df.file_path
            )
            result.changed_line_mappings.extend(mappings)
            result.ast_chunks.extend(chunks)
            result.diagnostics.extend(map_diags)

        result.metrics["ast_parse_ms"] = round((time.perf_counter() - t_ast) * 1000, 2)

        # 4. Context retrieval & ranking for each changed symbol / chunk
        t_ctx = time.perf_counter()
        for chunk in result.ast_chunks:
            context = self.context_ranker.build_relevant_context(
                repository_id=repository_id,
                commit_sha=head_sha,
                changed_file=chunk.file_path,
                changed_symbol=chunk.symbol_name,
                changed_chunk=chunk,
                graph=repository_graph,
                symbols=all_symbols or [],
            )
            result.context_by_symbol[chunk.symbol_name] = context

        result.metrics["context_build_ms"] = round((time.perf_counter() - t_ctx) * 1000, 2)
        result.metrics["total_analysis_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

        return result
