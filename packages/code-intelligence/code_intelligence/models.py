"""Core data models for Code Intelligence Engine."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DiffLineType(StrEnum):
    ADDED = "ADDED"
    DELETED = "DELETED"
    CONTEXT = "CONTEXT"


class LineSide(StrEnum):
    LEFT = "LEFT"    # Deleted lines from base
    RIGHT = "RIGHT"  # Added lines / context lines in head


class DiffLine(BaseModel):
    type: DiffLineType
    old_line: int | None = None
    new_line: int | None = None
    content: str


class DiffHunk(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine] = Field(default_factory=list)
    section_header: str = ""


class DiffFile(BaseModel):
    file_path: str
    old_path: str
    new_path: str
    change_type: str  # "added", "modified", "deleted", "renamed"
    is_binary: bool = False
    hunks: list[DiffHunk] = Field(default_factory=list)


class SymbolKind(StrEnum):
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    CLASS = "CLASS"
    INTERFACE = "INTERFACE"
    TYPE = "TYPE"
    MODULE = "MODULE"
    VARIABLE = "VARIABLE"


class ReferenceType(StrEnum):
    CALL = "CALL"
    IMPORT = "IMPORT"
    INHERITANCE = "INHERITANCE"
    IMPLEMENTATION = "IMPLEMENTATION"
    TYPE_REFERENCE = "TYPE_REFERENCE"
    ATTRIBUTE_REFERENCE = "ATTRIBUTE_REFERENCE"
    USES = "USES"


class DiagnosticStage(StrEnum):
    DIFF_PARSE = "DIFF_PARSE"
    FILE_READ = "FILE_READ"
    AST_PARSE = "AST_PARSE"
    SYMBOL_EXTRACTION = "SYMBOL_EXTRACTION"
    REFERENCE_RESOLUTION = "REFERENCE_RESOLUTION"
    GRAPH_UPDATE = "GRAPH_UPDATE"
    CONTEXT_BUILD = "CONTEXT_BUILD"


class DiagnosticSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ParserDiagnostic(BaseModel):
    file_path: str
    stage: DiagnosticStage
    error_type: str
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR


class ASTChunk(BaseModel):
    id: str
    repository_id: str | None = None
    file_path: str
    language: str
    node_type: str
    symbol_name: str
    start_line: int
    end_line: int
    start_byte: int
    end_byte: int
    source_code: str
    parent_symbol: str | None = None
    signature: str | None = None
    return_type: str | None = None
    parameters: list[dict[str, Any]] | None = None
    imports: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Symbol(BaseModel):
    symbol_id: str
    name: str
    kind: SymbolKind
    file_path: str
    start_line: int
    end_line: int
    start_byte: int | None = None
    end_byte: int | None = None
    signature: str | None = None
    return_type: str | None = None
    parameters: list[dict[str, Any]] | None = None
    parent_symbol: str | None = None
    language: str
    source_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SymbolReference(BaseModel):
    source_symbol: str
    target_symbol: str
    source_file: str
    target_file: str | None = None
    line_number: int
    reference_type: ReferenceType
    resolved: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class FileDependency(BaseModel):
    source_file: str
    target_file: str
    dependency_type: str = "IMPORTS"
    imported_symbols: list[str] = Field(default_factory=list)
    line_number: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class RankedContextItem(BaseModel):
    entity_type: str
    identifier: str
    file_path: str
    relevance_score: float
    reason: str
    content: str | None = None
    symbol_signature: str | None = None
    char_count: int = 0


class RelevantContext(BaseModel):
    repository_id: str
    commit_sha: str
    changed_file: str
    changed_symbol: str | None = None
    changed_chunk: ASTChunk | None = None
    parent_entity: str | None = None
    relevant_imports: list[str] = Field(default_factory=list)
    direct_callers: list[str] = Field(default_factory=list)
    direct_dependencies: list[str] = Field(default_factory=list)
    relevant_types: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    symbol_signatures: dict[str, str] = Field(default_factory=dict)
    ranked_items: list[RankedContextItem] = Field(default_factory=list)
    total_characters: int = 0
