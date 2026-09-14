"""Abstract base class for pluggable language parsers using Tree-sitter."""

from abc import ABC, abstractmethod

from code_intelligence.models import (
    ASTChunk,
    DiagnosticSeverity,
    DiagnosticStage,
    FileDependency,
    ParserDiagnostic,
    Symbol,
    SymbolReference,
)
from tree_sitter import Node, Tree


class LanguageParser(ABC):
    """Abstract interface for language-specific Tree-sitter AST analysis."""

    language_name: str = "unknown"

    @abstractmethod
    def parse(
        self, source_code: str | bytes, file_path: str = ""
    ) -> tuple[Tree | None, list[ParserDiagnostic]]:
        """Parse source code into a Tree-sitter Tree. Never raises exceptions."""

    @abstractmethod
    def extract_symbols(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[Symbol]:
        """Extract all top-level and member symbols (functions, methods, classes, types)."""

    @abstractmethod
    def extract_imports(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[FileDependency]:
        """Statically extract import statements and module dependencies."""

    @abstractmethod
    def extract_references(
        self, tree: Tree, source_bytes: bytes, file_path: str
    ) -> list[SymbolReference]:
        """Extract symbol references (calls, inheritance, instantiation) from the AST."""

    @abstractmethod
    def find_enclosing_chunk(
        self, tree: Tree, source_bytes: bytes, line_number: int, file_path: str
    ) -> ASTChunk | None:
        """
        Locate the smallest useful semantic entity enclosing the given 1-indexed line number.
        Prefers: Method / Function -> Class -> Module.
        """

    @staticmethod
    def get_node_text(node: Node, source_bytes: bytes) -> str:
        """Extract UTF-8 text from an AST node."""
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    @staticmethod
    def get_node_lines(node: Node) -> tuple[int, int]:
        """Convert Tree-sitter 0-indexed line numbers to 1-indexed inclusive line numbers."""
        return node.start_point.row + 1, node.end_point.row + 1

    @classmethod
    def check_tree_errors(
        cls, tree: Tree, file_path: str
    ) -> list[ParserDiagnostic]:
        """Check for syntax error nodes without terminating parsing."""
        diagnostics: list[ParserDiagnostic] = []
        if tree.root_node.has_error:
            diagnostics.append(
                ParserDiagnostic(
                    file_path=file_path,
                    stage=DiagnosticStage.AST_PARSE,
                    error_type="SyntaxWarning",
                    message=f"Tree-sitter detected syntax errors/missing nodes in '{file_path}'. Analysis continued gracefully.",
                    severity=DiagnosticSeverity.WARNING,
                )
            )
        return diagnostics
