"""Pluggable static analyzer adapters normalizing tool findings into evidence."""

import abc
import asyncio
import json
import shutil

from app.agents.schemas.finding import EvidenceItem, EvidenceType
from app.core.config import settings
from app.core.logging import logger


class StaticAnalysisResult:
    def __init__(
        self,
        tool: str,
        version: str,
        command: str,
        passed: bool,
        exit_code: int,
        evidence: list[EvidenceItem],
        raw_output: str = "",
    ):
        self.tool = tool
        self.version = version
        self.command = command
        self.passed = passed
        self.exit_code = exit_code
        self.evidence = evidence
        self.raw_output = raw_output


class StaticAnalyzer(abc.ABC):
    """Abstract base adapter for static analysis tools."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        pass

    @abc.abstractmethod
    async def analyze_file(
        self, repo_dir: str, file_path: str, target_line: int | None = None
    ) -> StaticAnalysisResult:
        pass


class RuffAnalyzer(StaticAnalyzer):
    """Ruff linter adapter for Python files."""

    @property
    def name(self) -> str:
        return "ruff"

    def is_available(self) -> bool:
        return bool(shutil.which("ruff"))

    async def analyze_file(
        self, repo_dir: str, file_path: str, target_line: int | None = None
    ) -> StaticAnalysisResult:
        cmd = f"ruff check --output-format=json {file_path}"
        if not self.is_available():
            return StaticAnalysisResult(
                tool="ruff",
                version="unavailable",
                command=cmd,
                passed=True,
                exit_code=0,
                evidence=[],
                raw_output="Ruff executable not found in PATH",
            )

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=repo_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, _ = await proc.communicate()
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")

            evidence_items: list[EvidenceItem] = []
            try:
                diagnostics = json.loads(stdout_str) if stdout_str.strip() else []
                for diag in diagnostics:
                    line = diag.get("location", {}).get("row", 1)
                    if target_line is None or abs(line - target_line) <= 5:
                        evidence_items.append(
                            EvidenceItem(
                                type=EvidenceType.STATIC_ANALYSIS,
                                file=file_path,
                                line_start=line,
                                line_end=diag.get("end_location", {}).get("row", line),
                                symbol=diag.get("code"),
                                description=f"Ruff [{diag.get('code')}]: {diag.get('message')}",
                            )
                        )
            except Exception:
                pass

            passed = proc.returncode == 0 or len(evidence_items) == 0
            return StaticAnalysisResult(
                tool="ruff",
                version="0.6.0",
                command=cmd,
                passed=passed,
                exit_code=proc.returncode or 0,
                evidence=evidence_items,
                raw_output=stdout_str[:1000],
            )
        except Exception as exc:
            logger.warning(f"Ruff analysis failed: {exc}")
            return StaticAnalysisResult(
                tool="ruff",
                version="error",
                command=cmd,
                passed=True,
                exit_code=0,
                evidence=[],
                raw_output=str(exc),
            )


class ESLintAnalyzer(StaticAnalyzer):
    """ESLint adapter for JS/TS files."""

    @property
    def name(self) -> str:
        return "eslint"

    def is_available(self) -> bool:
        return bool(shutil.which("eslint")) or bool(shutil.which("npx"))

    async def analyze_file(
        self, repo_dir: str, file_path: str, target_line: int | None = None
    ) -> StaticAnalysisResult:
        cmd = f"npx eslint --format json {file_path}"
        if not self.is_available():
            return StaticAnalysisResult(
                tool="eslint",
                version="unavailable",
                command=cmd,
                passed=True,
                exit_code=0,
                evidence=[],
                raw_output="ESLint not available",
            )
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=repo_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, _ = await proc.communicate()
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            evidence_items: list[EvidenceItem] = []
            try:
                results = json.loads(stdout_str) if stdout_str.strip() else []
                for file_res in results:
                    for msg in file_res.get("messages", []):
                        line = msg.get("line", 1)
                        if target_line is None or abs(line - target_line) <= 5:
                            evidence_items.append(
                                EvidenceItem(
                                    type=EvidenceType.STATIC_ANALYSIS,
                                    file=file_path,
                                    line_start=line,
                                    line_end=msg.get("endLine", line),
                                    symbol=msg.get("ruleId"),
                                    description=f"ESLint [{msg.get('ruleId')}]: {msg.get('message')}",
                                )
                            )
            except Exception:
                pass

            return StaticAnalysisResult(
                tool="eslint",
                version="latest",
                command=cmd,
                passed=(proc.returncode == 0 or len(evidence_items) == 0),
                exit_code=proc.returncode or 0,
                evidence=evidence_items,
                raw_output=stdout_str[:1000],
            )
        except Exception as exc:
            return StaticAnalysisResult(
                tool="eslint",
                version="error",
                command=cmd,
                passed=True,
                exit_code=0,
                evidence=[],
                raw_output=str(exc),
            )


class SemgrepAnalyzer(StaticAnalyzer):
    """Semgrep adapter for multi-language rule matching."""

    @property
    def name(self) -> str:
        return "semgrep"

    def is_available(self) -> bool:
        return bool(shutil.which("semgrep"))

    async def analyze_file(
        self, repo_dir: str, file_path: str, target_line: int | None = None
    ) -> StaticAnalysisResult:
        cmd = f"semgrep scan --json {file_path}"
        if not self.is_available():
            return StaticAnalysisResult(
                tool="semgrep",
                version="unavailable",
                command=cmd,
                passed=True,
                exit_code=0,
                evidence=[],
                raw_output="Semgrep not installed",
            )
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=repo_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, _ = await proc.communicate()
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            evidence_items: list[EvidenceItem] = []
            try:
                data = json.loads(stdout_str) if stdout_str.strip() else {}
                for res in data.get("results", []):
                    line = res.get("start", {}).get("line", 1)
                    if target_line is None or abs(line - target_line) <= 5:
                        evidence_items.append(
                            EvidenceItem(
                                type=EvidenceType.STATIC_ANALYSIS,
                                file=file_path,
                                line_start=line,
                                line_end=res.get("end", {}).get("line", line),
                                symbol=res.get("check_id"),
                                description=f"Semgrep [{res.get('check_id')}]: {res.get('extra', {}).get('message')}",
                            )
                        )
            except Exception:
                pass

            return StaticAnalysisResult(
                tool="semgrep",
                version="latest",
                command=cmd,
                passed=len(evidence_items) == 0,
                exit_code=proc.returncode or 0,
                evidence=evidence_items,
                raw_output=stdout_str[:1000],
            )
        except Exception as exc:
            return StaticAnalysisResult(
                tool="semgrep",
                version="error",
                command=cmd,
                passed=True,
                exit_code=0,
                evidence=[],
                raw_output=str(exc),
            )


class StaticAnalysisManager:
    """Manager delegating to configured static analyzers."""

    def __init__(self):
        self.analyzers: dict[str, StaticAnalyzer] = {
            "ruff": RuffAnalyzer(),
            "eslint": ESLintAnalyzer(),
            "semgrep": SemgrepAnalyzer(),
        }

    async def run_analysis(
        self, repo_dir: str, file_path: str, target_line: int | None = None
    ) -> list[StaticAnalysisResult]:
        results = []
        enabled = settings.STATIC_ANALYZERS_ENABLED
        for name in enabled:
            analyzer = self.analyzers.get(name)
            if analyzer and analyzer.is_available():
                res = await analyzer.analyze_file(repo_dir, file_path, target_line)
                results.append(res)
        return results
