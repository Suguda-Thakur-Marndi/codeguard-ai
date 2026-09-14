"""Deterministic mapping between changed diff lines and Tree-sitter AST semantic entities."""


from code_intelligence.languages.registry import default_registry
from code_intelligence.models import ASTChunk, DiffFile, DiffLineType, ParserDiagnostic


class DiffLineMapping:
    """Represents the semantic mapping for a single changed line."""

    def __init__(
        self,
        file_path: str,
        line_number: int,
        symbol_name: str,
        start_line: int,
        end_line: int,
        chunk: ASTChunk,
    ):
        self.file_path = file_path
        self.line_number = line_number
        self.symbol_name = symbol_name
        self.start_line = start_line
        self.end_line = end_line
        self.chunk = chunk

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "symbol_name": self.symbol_name,
            "ast_range": [self.start_line, self.end_line],
            "chunk_id": self.chunk.id,
        }


class DiffToASTMapper:
    """
    Deterministic mapper identifying enclosing semantic AST entities for changed lines.
    Ensures that modifications inside functions or classes yield the enclosing function/method,
    not merely the raw line number.
    """

    def __init__(self, registry=None):
        self.registry = registry or default_registry

    def map_file_diff_to_ast(
        self,
        diff_file: DiffFile,
        source_code: bytes,
        file_path: str | None = None,
    ) -> tuple[list[DiffLineMapping], list[ASTChunk], list[ParserDiagnostic]]:
        """
        For all added/changed lines in diff_file, determine their enclosing semantic AST entity.
        Returns:
          - mappings: list of line-to-entity mappings
          - unique_chunks: deduplicated ASTChunk objects with associated changed lines
          - diagnostics: any parser diagnostics encountered
        """
        mappings: list[DiffLineMapping] = []
        unique_chunks_by_id: dict[str, ASTChunk] = {}
        chunk_changed_lines: dict[str, set[int]] = {}
        diagnostics: list[ParserDiagnostic] = []

        target_path = file_path or diff_file.file_path
        parser = self.registry.get_parser(target_path)
        if not parser or not source_code:
            return mappings, [], diagnostics

        tree, parse_diags = parser.parse(source_code, file_path=target_path)
        diagnostics.extend(parse_diags)
        if not tree:
            return mappings, [], diagnostics

        # Collect changed (added) line numbers on the RIGHT side
        changed_lines: set[int] = set()
        for hunk in diff_file.hunks:
            for line in hunk.lines:
                if line.type == DiffLineType.ADDED and line.new_line is not None:
                    changed_lines.add(line.new_line)

        for line_num in sorted(changed_lines):
            chunk = parser.find_enclosing_chunk(tree, source_code, line_num, target_path)
            if chunk:
                mapping = DiffLineMapping(
                    file_path=target_path,
                    line_number=line_num,
                    symbol_name=chunk.symbol_name,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    chunk=chunk,
                )
                mappings.append(mapping)

                if chunk.id not in unique_chunks_by_id:
                    unique_chunks_by_id[chunk.id] = chunk
                    chunk_changed_lines[chunk.id] = set()
                chunk_changed_lines[chunk.id].add(line_num)

        # Attach changed lines to chunk metadata
        for chunk_id, chunk in unique_chunks_by_id.items():
            chunk.metadata["changed_lines"] = sorted(chunk_changed_lines.get(chunk_id, set()))

        return mappings, list(unique_chunks_by_id.values()), diagnostics
