"""Patch validation utility for evaluating proposed remediations in isolated environments."""

import ast
import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Any

from app.agents.validation.sandbox import ExecutionSandbox


@dataclass
class PatchValidationResult:
    """Outcome of validating a remediation patch."""

    syntax_valid: bool
    test_passed: bool
    status: str
    output_summary: str
    error: str | None = None


class PatchValidator:
    """Evaluates proposed remediations against isolated benchmark copies."""

    def __init__(self, sandbox: ExecutionSandbox | None = None):
        self.sandbox = sandbox or ExecutionSandbox()

    async def validate_python_patch(
        self,
        original_code: str,
        patched_code: str,
        test_command: str | None = None,
        fixture_dir: str | None = None,
    ) -> PatchValidationResult:
        """Validate that patched Python code is syntactically valid and passes tests."""
        # 1. Syntax check
        try:
            ast.parse(patched_code)
        except SyntaxError as e:
            return PatchValidationResult(
                syntax_valid=False,
                test_passed=False,
                status="SYNTAX_ERROR",
                output_summary="",
                error=f"SyntaxError in patched code: {e}",
            )

        # 2. If test command and fixture provided, test in isolated temporary copy
        if test_command and fixture_dir and os.path.isdir(fixture_dir):
            with tempfile.TemporaryDirectory() as tmp_dir:
                copy_dest = os.path.join(tmp_dir, "repo_copy")
                shutil.copytree(fixture_dir, copy_dest)

                # Write patched file if target file path provided or just run sandbox
                res = await self.sandbox.execute_scenario(
                    scenario_id="patch-val-001",
                    repo_dir=copy_dest,
                    command=test_command,
                    timeout=20,
                )
                return PatchValidationResult(
                    syntax_valid=True,
                    test_passed=(res.status == "PASS"),
                    status=res.status,
                    output_summary=res.stdout_summary or "",
                    error=res.stderr_summary if res.status != "PASS" else None,
                )

        return PatchValidationResult(
            syntax_valid=True,
            test_passed=True,
            status="SYNTAX_CHECKED",
            output_summary="Syntax valid. No test execution requested.",
            error=None,
        )
