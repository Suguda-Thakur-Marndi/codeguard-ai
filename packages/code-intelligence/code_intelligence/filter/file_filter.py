"""File filtering, path safety validation, binary detection, and large-file protection."""

import fnmatch
import os

DEFAULT_IGNORE_PATTERNS = [
    "*.git*",
    "*/.git/*",
    "node_modules/*",
    "*/node_modules/*",
    "dist/*",
    "*/dist/*",
    "build/*",
    "*/build/*",
    "coverage/*",
    "*/coverage/*",
    ".cache/*",
    "*/.cache/*",
    "venv/*",
    "*/venv/*",
    ".venv/*",
    "*/.venv/*",
    "__pycache__/*",
    "*/__pycache__/*",
    "*.pyc",
    "*.pyo",
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.bundle.js",
]

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".tar", ".gz",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso", ".woff", ".woff2", ".ttf",
    ".eot", ".mp3", ".mp4", ".mov", ".avi", ".sqlite", ".db", ".wasm",
}

# Production threshold limits
DEFAULT_MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB
DEFAULT_MAX_SOURCE_LINES = 5000
DEFAULT_MAX_AST_NODES = 20000


class FileFilter:
    """Production guard enforcing path validation, security, binary detection, and size limits."""

    def __init__(
        self,
        ignore_patterns: list[str] | None = None,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
        max_source_lines: int = DEFAULT_MAX_SOURCE_LINES,
        max_ast_nodes: int = DEFAULT_MAX_AST_NODES,
    ):
        self.ignore_patterns = list(ignore_patterns or DEFAULT_IGNORE_PATTERNS)
        self.max_file_size_bytes = max_file_size_bytes
        self.max_source_lines = max_source_lines
        self.max_ast_nodes = max_ast_nodes

    @staticmethod
    def is_safe_path(path: str) -> bool:
        """Validate path against directory traversal attacks (e.g. ../../)."""
        if not path or "\x00" in path:
            return False
        # Normalize slashes
        clean = path.replace("\\", "/").strip()
        parts = clean.split("/")
        # Disallow upward traversal
        depth = 0
        for part in parts:
            if part in ("", "."):
                continue
            if part == "..":
                depth -= 1
                if depth < 0:
                    return False
            else:
                depth += 1
        return True

    @staticmethod
    def sanitize_path(path: str) -> str:
        """Return canonicalized relative forward-slash path."""
        clean = path.replace("\\", "/").strip().lstrip("/")
        normalized = os.path.normpath(clean).replace("\\", "/")
        if normalized.startswith(".."):
            raise ValueError(f"Path traversal detected in path: '{path}'")
        return normalized

    def is_indexable_file(self, path: str) -> bool:
        """Check if file should be indexed based on ignore patterns and extension."""
        if not self.is_safe_path(path):
            return False

        norm_path = path.replace("\\", "/").strip().lstrip("/")

        # Check binary extensions
        _, ext = os.path.splitext(norm_path.lower())
        if ext in BINARY_EXTENSIONS:
            return False

        # Match ignore patterns
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(norm_path, pattern) or fnmatch.fnmatch(os.path.basename(norm_path), pattern):
                return False

        return True

    @staticmethod
    def is_binary(content: bytes) -> bool:
        """Heuristic detection of binary files via null bytes in the first 8KB."""
        if not content:
            return False
        chunk = content[:8192]
        if b"\x00" in chunk:
            return True
        # Try UTF-8 decoding sample
        try:
            chunk.decode("utf-8")
        except UnicodeDecodeError:
            # Over 30% non-ascii non-printable control chars indicates binary
            control_chars = sum(1 for byte in chunk if byte < 32 and byte not in (9, 10, 13))
            if control_chars / len(chunk) > 0.3:
                return True
        return False

    def check_file_limits(self, file_path: str, content: bytes) -> tuple[bool, str | None]:
        """Verify file does not exceed safety thresholds."""
        if len(content) > self.max_file_size_bytes:
            return False, f"File size {len(content)} bytes exceeds limit {self.max_file_size_bytes} bytes"

        line_count = content.count(b"\n") + (1 if content and not content.endswith(b"\n") else 0)
        if line_count > self.max_source_lines:
            return False, f"File has {line_count} lines, exceeding limit of {self.max_source_lines} lines"

        return True, None
