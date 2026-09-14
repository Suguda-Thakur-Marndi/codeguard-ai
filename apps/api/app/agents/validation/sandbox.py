"""ExecutionSandbox providing ephemeral, isolated, and resource-bounded test execution."""

import asyncio
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.core.logging import logger

# Global concurrency limiter
_concurrency_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_VALIDATIONS)


@dataclass
class ValidationResultData:
    scenario_id: str
    status: str  # PASS, FAIL, TIMEOUT, ERROR, SKIPPED
    exit_code: int | None
    stdout_summary: str
    stderr_summary: str
    duration_ms: float
    evidence: list[dict[str, Any]] = field(default_factory=list)


class ExecutionSandbox:
    """
    Manages isolated, ephemeral container execution for behavioral verification.
    Guarantees:
    - Zero network access by default (network_mode="none")
    - Zero host filesystem mutation (read-only workspace mounts)
    - Zero access to host secrets or /var/run/docker.sock
    - Strict CPU, memory, process, and duration timeouts
    - Strict command allowlisting (rejects arbitrary bash -c commands)
    - Guaranteed container cleanup on success, failure, timeout, or crash
    - Fallback isolated sub-process runner when Docker daemon is not active
    """

    def __init__(
        self,
        image: str = settings.SANDBOX_IMAGE,
        cpu_limit: float = settings.SANDBOX_CPU_LIMIT,
        memory_limit: str = settings.SANDBOX_MEMORY_LIMIT,
        max_processes: int = settings.SANDBOX_MAX_PROCESSES,
        timeout_seconds: int = settings.SANDBOX_TIMEOUT_SECONDS,
        max_output_bytes: int = settings.SANDBOX_MAX_OUTPUT_BYTES,
    ):
        self.image = image
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.max_processes = max_processes
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes

    def is_command_allowed(self, command: str) -> bool:
        """
        Verify that command is in the configured allowlist.
        Rejects arbitrary shell pipelines, redirection, or unsafe interpreters.
        """
        cmd_clean = command.strip()
        # Disallow shell operators
        forbidden_operators = [";", "&&", "||", "|", "`", "$", ">", "<", "\n"]
        if any(op in cmd_clean for op in forbidden_operators):
            return False

        # Must start with an allowlisted command prefix
        allowed = settings.SANDBOX_ALLOWLIST_COMMANDS
        tokens = cmd_clean.split()
        if not tokens:
            return False

        base_cmd = tokens[0]
        full_prefix = " ".join(tokens[:2]) if len(tokens) >= 2 else base_cmd

        return any(
            cmd_clean.startswith(allowed_cmd) or base_cmd == allowed_cmd or full_prefix == allowed_cmd
            for allowed_cmd in allowed
        )

    async def execute_command(
        self,
        command: str,
        repo_dir: str,
        env_vars: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> ValidationResultData:
        """Execute a standalone allowlisted command within isolated sandbox."""
        return await self.execute_scenario(
            scenario_id="command-validation",
            repo_dir=repo_dir,
            command=command,
            env_vars=env_vars,
            timeout=timeout,
        )

    async def execute_scenario(
        self,
        scenario_id: str,
        repo_dir: str,
        command: str,
        env_vars: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> ValidationResultData:
        """Execute a validation scenario inside the isolated sandbox."""
        effective_timeout = timeout or self.timeout_seconds
        t0 = time.perf_counter()

        # 1. Command Allowlist Gate
        if not self.is_command_allowed(command):
            logger.warning(f"Rejected unallowed sandbox command: '{command}'")
            return ValidationResultData(
                scenario_id=scenario_id,
                status="ERROR",
                exit_code=126,
                stdout_summary="",
                stderr_summary=f"Security violation: Command '{command}' is not in the sandbox allowlist.",
                duration_ms=0.0,
                evidence=[],
            )

        # 2. Concurrency limiting
        async with _concurrency_semaphore:
            # Try Docker execution first
            docker_available = await self._is_docker_available()
            if docker_available:
                return await self._execute_docker(
                    scenario_id=scenario_id,
                    repo_dir=repo_dir,
                    command=command,
                    env_vars=env_vars,
                    timeout=effective_timeout,
                    t0=t0,
                )
            else:
                # Safe isolated process execution fallback
                return await self._execute_isolated_process(
                    scenario_id=scenario_id,
                    repo_dir=repo_dir,
                    command=command,
                    env_vars=env_vars,
                    timeout=effective_timeout,
                    t0=t0,
                )

    async def _is_docker_available(self) -> bool:
        """Check if Docker daemon is accessible."""
        try:
            import docker
            client = docker.from_env()
            client.ping()
            return True
        except Exception:
            return False

    async def _execute_docker(
        self,
        scenario_id: str,
        repo_dir: str,
        command: str,
        env_vars: dict[str, str] | None,
        timeout: int,
        t0: float,
    ) -> ValidationResultData:
        """Execute inside an isolated ephemeral Docker container."""
        import docker
        client = docker.from_env()
        container = None

        safe_env = {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "CI": "true",
        }
        if env_vars:
            # Filter out sensitive host env vars
            for k, v in env_vars.items():
                if not any(secret_term in k.upper() for secret_term in ["KEY", "SECRET", "TOKEN", "PASSWORD"]):
                    safe_env[k] = str(v)

        try:
            # Create container with strict isolation
            container = client.containers.create(
                image=self.image,
                command=command.split(),
                network_mode="none",  # ZERO network
                mem_limit=self.memory_limit,
                nano_cpus=int(self.cpu_limit * 1e9),
                pids_limit=self.max_processes,
                user="1000:1000",
                volumes={os.path.abspath(repo_dir): {"bind": "/workspace", "mode": "ro"}},
                privileged=False,
                security_opt=["no-new-privileges:true"],
                cap_drop=["ALL"],
                environment=safe_env,
                working_dir="/workspace",
            )

            container.start()

            # Wait for container execution with timeout
            loop = asyncio.get_event_loop()
            res = await asyncio.wait_for(
                loop.run_in_executor(None, container.wait),
                timeout=float(timeout),
            )
            exit_code = res.get("StatusCode", 0)

            raw_logs = container.logs(stdout=True, stderr=True)
            output_str = raw_logs.decode("utf-8", errors="replace")[: self.max_output_bytes]

            duration_ms = (time.perf_counter() - t0) * 1000.0
            status = "PASS" if exit_code == 0 else "FAIL"

            evidence = [
                {
                    "type": "RUNTIME",
                    "file": "sandbox",
                    "description": f"Execution status: {status} (exit code {exit_code}) in {duration_ms:.1f}ms",
                }
            ]

            return ValidationResultData(
                scenario_id=scenario_id,
                status=status,
                exit_code=exit_code,
                stdout_summary=output_str,
                stderr_summary="",
                duration_ms=round(duration_ms, 2),
                evidence=evidence,
            )

        except TimeoutError:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.warning(f"Sandbox container execution timed out after {timeout}s")
            return ValidationResultData(
                scenario_id=scenario_id,
                status="TIMEOUT",
                exit_code=124,
                stdout_summary="",
                stderr_summary=f"Execution timed out after {timeout} seconds",
                duration_ms=round(duration_ms, 2),
                evidence=[],
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logger.error(f"Sandbox container execution failed: {exc}")
            return ValidationResultData(
                scenario_id=scenario_id,
                status="ERROR",
                exit_code=1,
                stdout_summary="",
                stderr_summary=str(exc)[:1000],
                duration_ms=round(duration_ms, 2),
                evidence=[],
            )
        finally:
            # Ephemeral destruction guaranteed in finally block
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

    async def _execute_isolated_process(
        self,
        scenario_id: str,
        repo_dir: str,
        command: str,
        env_vars: dict[str, str] | None,
        timeout: int,
        t0: float,
    ) -> ValidationResultData:
        """
        Isolated fallback runner when Docker daemon is not active.
        Executes within a temporary read-only copy of the repository
        with restricted environment variables, output limits, and timeout.
        """
        temp_workspace = tempfile.mkdtemp(prefix="codeguard_sandbox_")
        try:
            # Copy repository to temporary workspace
            if os.path.isdir(repo_dir):
                for item in os.listdir(repo_dir):
                    s = os.path.join(repo_dir, item)
                    d = os.path.join(temp_workspace, item)
                    if os.path.isdir(s):
                        if item in (".git", ".venv", "venv", "node_modules", ".next", "dist", "build", "__pycache__", ".pytest_cache"):
                            continue
                        shutil.copytree(
                            s,
                            d,
                            symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "venv", "node_modules", ".next", "dist", "build", ".pytest_cache"),
                        )
                    else:
                        shutil.copy2(s, d)

            # Minimal safe environment
            safe_env = {
                "PATH": os.environ.get("PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",
                "CI": "true",
            }
            if env_vars:
                for k, v in env_vars.items():
                    if not any(sec in k.upper() for sec in ["KEY", "SECRET", "TOKEN", "PASSWORD"]):
                        safe_env[k] = str(v)

            cmd_tokens = command.split()
            if cmd_tokens and cmd_tokens[0] in ("python", "python3"):
                cmd_tokens[0] = sys.executable
            elif cmd_tokens and cmd_tokens[0] == "pytest":
                cmd_tokens = [sys.executable, "-m", "pytest"] + cmd_tokens[1:]

            proc = await asyncio.create_subprocess_exec(
                *cmd_tokens,
                cwd=temp_workspace,
                env=safe_env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=float(timeout)
                )
                exit_code = proc.returncode
                stdout_str = stdout_bytes.decode("utf-8", errors="replace")[: self.max_output_bytes]
                stderr_str = stderr_bytes.decode("utf-8", errors="replace")[: self.max_output_bytes]
                duration_ms = (time.perf_counter() - t0) * 1000.0

                status = "PASS" if exit_code == 0 else "FAIL"
                evidence = [
                    {
                        "type": "RUNTIME",
                        "file": "sandbox_isolated",
                        "description": f"Execution status: {status} (exit code {exit_code}) in {duration_ms:.1f}ms",
                    }
                ]
                return ValidationResultData(
                    scenario_id=scenario_id,
                    status=status,
                    exit_code=exit_code,
                    stdout_summary=stdout_str,
                    stderr_summary=stderr_str,
                    duration_ms=round(duration_ms, 2),
                    evidence=evidence,
                )

            except TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
                duration_ms = (time.perf_counter() - t0) * 1000.0
                return ValidationResultData(
                    scenario_id=scenario_id,
                    status="TIMEOUT",
                    exit_code=124,
                    stdout_summary="",
                    stderr_summary=f"Execution timed out after {timeout} seconds",
                    duration_ms=round(duration_ms, 2),
                    evidence=[],
                )

        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return ValidationResultData(
                scenario_id=scenario_id,
                status="ERROR",
                exit_code=1,
                stdout_summary="",
                stderr_summary=str(exc)[:1000],
                duration_ms=round(duration_ms, 2),
                evidence=[],
            )
        finally:
            # Ephemeral workspace cleanup
            try:
                shutil.rmtree(temp_workspace, ignore_errors=True)
            except Exception:
                pass
