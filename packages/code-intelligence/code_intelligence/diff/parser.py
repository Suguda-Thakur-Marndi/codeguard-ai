"""Unified diff parser transforming raw diff text into structured typed models."""

import re

from code_intelligence.models import (
    DiagnosticSeverity,
    DiagnosticStage,
    DiffFile,
    DiffHunk,
    DiffLine,
    DiffLineType,
    ParserDiagnostic,
)
from unidiff import PatchSet
from unidiff.errors import UnidiffParseError


def _clean_path(path: str | None) -> str:
    """Normalize git diff path by stripping standard git prefixes (a/, b/) or /dev/null."""
    if not path or path == "/dev/null":
        return ""
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


class UnifiedDiffParser:
    """Parser for Unified Git Diffs producing typed DiffFile, DiffHunk, and DiffLine models."""

    @classmethod
    def parse(cls, raw_diff: str) -> tuple[list[DiffFile], list[ParserDiagnostic]]:
        """
        Parse raw unified diff string into structured DiffFile models and diagnostics.
        Gracefully handles syntax errors, binary files, renames, and deletions without raising exceptions.
        """
        diagnostics: list[ParserDiagnostic] = []
        parsed_files: list[DiffFile] = []

        if not raw_diff or not raw_diff.strip():
            return parsed_files, diagnostics

        try:
            patch_set = PatchSet(raw_diff)
        except UnidiffParseError as exc:
            diagnostics.append(
                ParserDiagnostic(
                    file_path="<diff>",
                    stage=DiagnosticStage.DIFF_PARSE,
                    error_type="UnidiffParseError",
                    message=f"Failed to parse unified diff: {exc!s}",
                    severity=DiagnosticSeverity.ERROR,
                )
            )
            # Attempt fallback hunk-by-hunk / file-by-file extraction
            return cls._fallback_parse(raw_diff, diagnostics)
        except Exception as exc:  # noqa: BLE001
            diagnostics.append(
                ParserDiagnostic(
                    file_path="<diff>",
                    stage=DiagnosticStage.DIFF_PARSE,
                    error_type=exc.__class__.__name__,
                    message=f"Unexpected error parsing diff: {exc!s}",
                    severity=DiagnosticSeverity.ERROR,
                )
            )
            return parsed_files, diagnostics

        for patched_file in patch_set:
            old_path = _clean_path(patched_file.source_file)
            new_path = _clean_path(patched_file.target_file)

            if patched_file.is_added_file:
                change_type = "added"
                primary_path = new_path
            elif patched_file.is_removed_file:
                change_type = "deleted"
                primary_path = old_path
            elif patched_file.is_rename:
                change_type = "renamed"
                primary_path = new_path or old_path
            else:
                change_type = "modified"
                primary_path = new_path or old_path

            hunks: list[DiffHunk] = []
            if not patched_file.is_binary_file:
                for hunk in patched_file:
                    diff_lines: list[DiffLine] = []
                    for line in hunk:
                        if line.is_added:
                            line_type = DiffLineType.ADDED
                            old_line_no = None
                            new_line_no = line.target_line_no
                        elif line.is_removed:
                            line_type = DiffLineType.DELETED
                            old_line_no = line.source_line_no
                            new_line_no = None
                        else:
                            line_type = DiffLineType.CONTEXT
                            old_line_no = line.source_line_no
                            new_line_no = line.target_line_no

                        diff_lines.append(
                            DiffLine(
                                type=line_type,
                                old_line=old_line_no,
                                new_line=new_line_no,
                                content=line.value.rstrip("\r\n"),
                            )
                        )

                    hunks.append(
                        DiffHunk(
                            old_start=hunk.source_start,
                            old_count=hunk.source_length,
                            new_start=hunk.target_start,
                            new_count=hunk.target_length,
                            lines=diff_lines,
                            section_header=getattr(hunk, "section_header", "") or "",
                        )
                    )

            parsed_files.append(
                DiffFile(
                    file_path=primary_path,
                    old_path=old_path,
                    new_path=new_path,
                    change_type=change_type,
                    is_binary=patched_file.is_binary_file,
                    hunks=hunks,
                )
            )

        return parsed_files, diagnostics

    @classmethod
    def _fallback_parse(
        cls, raw_diff: str, diagnostics: list[ParserDiagnostic]
    ) -> tuple[list[DiffFile], list[ParserDiagnostic]]:
        """Simple regex-based fallback parser for broken diff chunks to recover partial file changes."""
        parsed_files: list[DiffFile] = []
        file_chunks = re.split(r"(?=diff --git )", raw_diff)

        for chunk in file_chunks:
            if not chunk.strip():
                continue
            try:
                sub_files, sub_diag = cls.parse(chunk)
                parsed_files.extend(sub_files)
                diagnostics.extend(sub_diag)
            except Exception:  # noqa: BLE001
                # Extract file name via regex
                match = re.search(r"diff --git a/(.+?) b/(.+)", chunk)
                file_path = match.group(2).strip() if match else "<unknown>"
                diagnostics.append(
                    ParserDiagnostic(
                        file_path=file_path,
                        stage=DiagnosticStage.DIFF_PARSE,
                        error_type="UnrecoverableDiffChunk",
                        message=f"Could not parse diff chunk for {file_path}",
                        severity=DiagnosticSeverity.WARNING,
                    )
                )

        return parsed_files, diagnostics
