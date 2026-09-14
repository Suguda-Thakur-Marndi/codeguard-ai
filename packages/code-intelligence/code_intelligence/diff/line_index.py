"""Deterministic index of valid review lines for PR diffs distinguishing LEFT vs RIGHT sides."""


from code_intelligence.models import DiffFile, DiffHunk, DiffLineType, LineSide


class ChangedLineIndex:
    """
    Deterministic index of valid review lines for GitHub inline PR commenting.
    Distinguishes:
      - RIGHT: Head file lines (additions + context lines present in hunks)
      - LEFT: Base file lines (deletions + context lines present in hunks)
    Prevents commenting on arbitrary, unchanged, or out-of-diff lines.
    """

    def __init__(self, diff_files: list[DiffFile] | None = None):
        # file_path -> { "RIGHT": set[int], "LEFT": set[int] }
        self._index: dict[str, dict[str, set[int]]] = {}
        # (file_path, side, line_no) -> DiffHunk
        self._hunk_lookup: dict[tuple[str, str, int], DiffHunk] = {}
        # Also map only added lines for AST semantic expansion
        self._added_lines: dict[str, set[int]] = {}

        if diff_files:
            self.build_index(diff_files)

    def build_index(self, diff_files: list[DiffFile]) -> None:
        """Construct the deterministic index from parsed DiffFile objects."""
        self._index.clear()
        self._hunk_lookup.clear()
        self._added_lines.clear()

        for diff_file in diff_files:
            file_path = diff_file.file_path
            if not file_path:
                continue

            self._index[file_path] = {
                LineSide.RIGHT.value: set(),
                LineSide.LEFT.value: set(),
            }
            self._added_lines[file_path] = set()

            for hunk in diff_file.hunks:
                for line in hunk.lines:
                    if line.type == DiffLineType.ADDED and line.new_line is not None:
                        self._index[file_path][LineSide.RIGHT.value].add(line.new_line)
                        self._hunk_lookup[(file_path, LineSide.RIGHT.value, line.new_line)] = hunk
                        self._added_lines[file_path].add(line.new_line)

                    elif line.type == DiffLineType.DELETED and line.old_line is not None:
                        self._index[file_path][LineSide.LEFT.value].add(line.old_line)
                        self._hunk_lookup[(file_path, LineSide.LEFT.value, line.old_line)] = hunk

                    elif line.type == DiffLineType.CONTEXT:
                        if line.new_line is not None:
                            self._index[file_path][LineSide.RIGHT.value].add(line.new_line)
                            self._hunk_lookup[(file_path, LineSide.RIGHT.value, line.new_line)] = hunk
                        if line.old_line is not None:
                            self._index[file_path][LineSide.LEFT.value].add(line.old_line)
                            self._hunk_lookup[(file_path, LineSide.LEFT.value, line.old_line)] = hunk

    def is_valid_review_line(
        self, file_path: str, line_number: int, side: LineSide | str = LineSide.RIGHT
    ) -> bool:
        """Determine if a line number in a file is a valid commentable position in this PR."""
        side_val = side.value if isinstance(side, LineSide) else str(side).upper()
        file_entries = self._index.get(file_path)
        if not file_entries:
            return False
        return line_number in file_entries.get(side_val, set())

    def get_valid_lines(
        self, file_path: str, side: LineSide | str = LineSide.RIGHT
    ) -> list[int]:
        """Return sorted list of valid review lines for a file and side."""
        side_val = side.value if isinstance(side, LineSide) else str(side).upper()
        file_entries = self._index.get(file_path)
        if not file_entries:
            return []
        return sorted(file_entries.get(side_val, set()))

    def get_added_lines(self, file_path: str) -> list[int]:
        """Return sorted list of specifically added lines in the head file."""
        return sorted(self._added_lines.get(file_path, set()))

    def get_hunk_for_line(
        self, file_path: str, line_number: int, side: LineSide | str = LineSide.RIGHT
    ) -> DiffHunk | None:
        """Retrieve the enclosing DiffHunk for a given line number."""
        side_val = side.value if isinstance(side, LineSide) else str(side).upper()
        return self._hunk_lookup.get((file_path, side_val, line_number))

    def to_dict(self) -> dict[str, dict[str, list[int]]]:
        """Serialize index into deterministic JSON-serializable dictionary."""
        result: dict[str, dict[str, list[int]]] = {}
        for file_path, sides in sorted(self._index.items()):
            result[file_path] = {
                LineSide.RIGHT.value: sorted(sides[LineSide.RIGHT.value]),
                LineSide.LEFT.value: sorted(sides[LineSide.LEFT.value]),
            }
        return result
