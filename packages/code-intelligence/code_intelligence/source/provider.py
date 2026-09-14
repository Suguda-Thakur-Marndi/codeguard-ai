"""Repository source code acquisition layer."""

import os
import subprocess
from abc import ABC, abstractmethod
from typing import Any

from code_intelligence.filter.file_filter import FileFilter


class RepositorySourceProvider(ABC):
    """Abstract interface for acquiring repository source files at a specific commit."""

    @abstractmethod
    def checkout_commit(self, commit_sha: str) -> bool:
        """Switch workspace or internal state to target commit SHA."""

    @abstractmethod
    def get_file(self, file_path: str, commit_sha: str | None = None) -> bytes | None:
        """Retrieve the raw content of a specific file at commit_sha."""

    @abstractmethod
    def get_files(self, commit_sha: str | None = None) -> dict[str, bytes]:
        """Retrieve all indexable files in the repository at commit_sha."""

    @abstractmethod
    def get_commit_metadata(self, commit_sha: str | None = None) -> dict[str, Any]:
        """Retrieve commit metadata (author, message, date, sha)."""


class MemoryRepositorySourceProvider(RepositorySourceProvider):
    """In-memory source provider for unit tests and synthetic fixtures."""

    def __init__(
        self,
        files_by_commit: dict[str, dict[str, bytes]] | None = None,
        default_files: dict[str, bytes] | None = None,
        metadata_by_commit: dict[str, dict[str, Any]] | None = None,
    ):
        self._files_by_commit = files_by_commit or {}
        self._default_files = default_files or {}
        self._metadata = metadata_by_commit or {}
        self._current_commit = "HEAD"

    def set_commit_files(self, commit_sha: str, files: dict[str, bytes]) -> None:
        self._files_by_commit[commit_sha] = files

    def checkout_commit(self, commit_sha: str) -> bool:
        self._current_commit = commit_sha
        return True

    def get_file(self, file_path: str, commit_sha: str | None = None) -> bytes | None:
        sha = commit_sha or self._current_commit
        commit_files = self._files_by_commit.get(sha, self._default_files)
        clean_path = FileFilter.sanitize_path(file_path)
        return commit_files.get(clean_path)

    def get_files(self, commit_sha: str | None = None) -> dict[str, bytes]:
        sha = commit_sha or self._current_commit
        return dict(self._files_by_commit.get(sha, self._default_files))

    def get_commit_metadata(self, commit_sha: str | None = None) -> dict[str, Any]:
        sha = commit_sha or self._current_commit
        return self._metadata.get(sha, {"sha": sha, "author": "dev", "message": "Test commit"})


class LocalDiskRepositorySourceProvider(RepositorySourceProvider):
    """File-system based repository source provider with path safety."""

    def __init__(self, root_dir: str, file_filter: FileFilter | None = None):
        self.root_dir = os.path.abspath(root_dir)
        self.filter = file_filter or FileFilter()
        self._current_commit: str = "HEAD"

    def checkout_commit(self, commit_sha: str) -> bool:
        """If this is a git directory, checkout the target commit."""
        self._current_commit = commit_sha
        git_dir = os.path.join(self.root_dir, ".git")
        if os.path.exists(git_dir):
            try:
                res = subprocess.run(
                    ["git", "checkout", commit_sha],
                    cwd=self.root_dir,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                return res.returncode == 0
            except Exception:  # noqa: BLE001
                return False
        return True

    def get_file(self, file_path: str, commit_sha: str | None = None) -> bytes | None:
        clean_path = FileFilter.sanitize_path(file_path)
        full_path = os.path.join(self.root_dir, clean_path)
        # Prevent traversal outside root_dir
        if not os.path.abspath(full_path).startswith(self.root_dir):
            return None
        if not os.path.isfile(full_path):
            return None
        try:
            with open(full_path, "rb") as f:
                return f.read()
        except OSError:
            return None

    def get_files(self, commit_sha: str | None = None) -> dict[str, bytes]:
        files: dict[str, bytes] = {}
        for root, _, filenames in os.walk(self.root_dir):
            for filename in filenames:
                rel_dir = os.path.relpath(root, self.root_dir).replace("\\", "/")
                rel_path = filename if rel_dir == "." else f"{rel_dir}/{filename}"
                if not self.filter.is_indexable_file(rel_path):
                    continue
                content = self.get_file(rel_path)
                if content is not None and not self.filter.is_binary(content):
                    files[rel_path] = content
        return files

    def get_commit_metadata(self, commit_sha: str | None = None) -> dict[str, Any]:
        sha = commit_sha or self._current_commit
        return {
            "sha": sha,
            "root_dir": self.root_dir,
        }
