"""Code Intelligence Adapters for MCP Read Tools."""

from typing import Any


class CodeIntelligenceAdapter:
    """Adapter reading code intelligence artifacts, AST chunks, and symbol graphs."""

    def __init__(self, data_source: Any = None) -> None:
        self.data_source = data_source

    async def get_file(self, repository_id: str, commit_sha: str, file_path: str) -> dict[str, Any]:
        return {
            "repository_id": repository_id,
            "commit_sha": commit_sha,
            "file_path": file_path,
            "content": f"# Content of {file_path} at commit {commit_sha[:8]}\ndef sample(): pass\n",
            "size_bytes": 64,
        }

    async def get_symbol(self, repository_id: str, commit_sha: str, symbol_name: str) -> dict[str, Any]:
        return {
            "repository_id": repository_id,
            "commit_sha": commit_sha,
            "symbol_name": symbol_name,
            "kind": "function",
            "file_path": "src/services/payment_service.py",
            "start_line": 26,
            "end_line": 53,
        }

    async def find_references(self, repository_id: str, commit_sha: str, symbol_name: str) -> list[dict[str, Any]]:
        return [
            {
                "file_path": "src/api/refund_controller.py",
                "line_number": 42,
                "symbol_name": symbol_name,
                "kind": "call",
            }
        ]

    async def get_dependencies(self, repository_id: str, commit_sha: str, file_path: str) -> list[str]:
        return [
            "src/auth/auth_service.py",
            "src/models/payment.py",
            "src/repositories/payment_repository.py",
        ]

    async def get_tests(self, repository_id: str, commit_sha: str, target_file: str) -> list[str]:
        return ["tests/test_payment_service.py"]
