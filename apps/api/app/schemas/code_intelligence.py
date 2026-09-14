"""Pydantic schemas for Code Intelligence Engine APIs."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.repository_index import IndexStatus


class RepositoryIndexRead(BaseModel):
    """Schema for repository indexing state and telemetry."""

    id: str
    repository_id: str
    commit_sha: str
    status: IndexStatus
    last_indexed_commit: str | None = None
    index_started_at: datetime | None = None
    index_completed_at: datetime | None = None
    files_processed: int = 0
    files_failed: int = 0
    error_count: int = 0
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IndexTriggerRequest(BaseModel):
    """Schema for requesting repository indexing."""

    commit_sha: str | None = Field(None, description="Target commit SHA (defaults to default branch HEAD)")
    force_reindex: bool = Field(False, description="Force full re-indexing ignoring prior index cache")


class CodeSymbolRead(BaseModel):
    """Schema for code symbols."""

    id: str
    repository_id: str
    commit_sha: str
    file_path: str
    name: str
    kind: str
    language: str
    start_line: int
    end_line: int
    start_byte: int | None = None
    end_byte: int | None = None
    signature: str | None = None
    return_type: str | None = None
    parameters: list[dict[str, Any]] | None = None
    parent_symbol: str | None = None
    source_code: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class SymbolReferenceRead(BaseModel):
    """Schema for symbol references."""

    id: str
    repository_id: str
    commit_sha: str
    source_symbol: str
    target_symbol: str
    source_file: str
    target_file: str | None = None
    line_number: int
    reference_type: str
    resolved: bool
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class FileDependencyRead(BaseModel):
    """Schema for file dependencies."""

    id: str
    repository_id: str
    commit_sha: str
    source_file: str
    target_file: str
    dependency_type: str
    imported_symbols: list[str] = Field(default_factory=list)
    line_number: int
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class DiffLineSchema(BaseModel):
    type: str
    old_line: int | None = None
    new_line: int | None = None
    content: str


class DiffHunkSchema(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLineSchema] = Field(default_factory=list)
    section_header: str = ""


class DiffFileSchema(BaseModel):
    file_path: str
    old_path: str
    new_path: str
    change_type: str
    is_binary: bool = False
    hunks: list[DiffHunkSchema] = Field(default_factory=list)


class ASTChunkSchema(BaseModel):
    id: str
    file_path: str
    language: str
    node_type: str
    symbol_name: str
    start_line: int
    end_line: int
    signature: str | None = None
    return_type: str | None = None
    parent_symbol: str | None = None
    source_code: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChangedLineIndexSchema(BaseModel):
    # file_path -> { "RIGHT": list[int], "LEFT": list[int] }
    index: dict[str, dict[str, list[int]]] = Field(default_factory=dict)


class RankedContextItemSchema(BaseModel):
    entity_type: str
    identifier: str
    file_path: str
    relevance_score: float
    reason: str
    content: str | None = None
    symbol_signature: str | None = None
    char_count: int = 0


class RelevantContextSchema(BaseModel):
    repository_id: str
    commit_sha: str
    changed_file: str
    changed_symbol: str | None = None
    changed_chunk: ASTChunkSchema | None = None
    parent_entity: str | None = None
    relevant_imports: list[str] = Field(default_factory=list)
    direct_callers: list[str] = Field(default_factory=list)
    direct_dependencies: list[str] = Field(default_factory=list)
    relevant_types: list[str] = Field(default_factory=list)
    related_files: list[str] = Field(default_factory=list)
    symbol_signatures: dict[str, str] = Field(default_factory=dict)
    ranked_items: list[RankedContextItemSchema] = Field(default_factory=list)
    total_characters: int = 0
