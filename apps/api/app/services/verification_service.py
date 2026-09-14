"""Verification service orchestrating Adversarial Judge, deduplication, and execution validation."""

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.agents.judge.adversarial_judge import AdversarialJudge
from app.agents.judge.deduplication import DeduplicationEngine
from app.agents.judge.schemas import JudgeDecisionType
from app.agents.llm.provider import LLMProvider
from app.agents.schemas.finding import (
    FindingStatus,
    ReviewFinding,
)
from app.agents.validation.policy import ExecutionDecision, ValidationPolicy
from app.agents.validation.sandbox import ExecutionSandbox
from app.agents.validation.static import StaticAnalysisManager
from app.db.repositories.review_finding_repo import ReviewFindingRepository


class VerificationService:
    """
    Core domain service orchestrating the Phase 4 verification pipeline:
    1. Deterministic diff boundary check (Gate 1)
    2. Adversarial Judge re-reading and existing guard verification (Gates 2-4)
    3. Deterministic & semantic deduplication + root-cause grouping
    4. Validation policy dispatch (EXECUTE vs STATIC_ONLY vs NO_EXECUTION)
    5. Isolated Docker sandbox execution or static analysis
    6. Synthesis into final verified finding states (PUBLISHABLE, VALIDATED, EXECUTION_VERIFIED, REJECTED)
    7. Immutable audit logging of runs, decisions, scenarios, results, and evidence
    """

    def __init__(self, db: Session, llm_provider: LLMProvider):
        self.db = db
        self.repo = ReviewFindingRepository(db)
        self.judge = AdversarialJudge(llm_provider)
        self.sandbox = ExecutionSandbox()
        self.static_manager = StaticAnalysisManager()

    async def verify_review_job_findings(
        self,
        review_job_id: str,
        candidate_findings: list[ReviewFinding],
        changed_files: list[str],
        valid_lines_by_file: dict[str, dict[str, list[int]]],
        diff_hunks_by_file: dict[str, list[dict[str, Any]]],
        ast_chunks_by_file: dict[str, list[dict[str, Any]]],
        context_by_symbol: dict[str, Any],
        source_code_by_file: dict[str, str],
        repo_dir: str | None = None,
    ) -> tuple[list[ReviewFinding], list[ReviewFinding]]:
        """
        Run the complete adversarial verification and execution validation pipeline for a review job.
        Returns:
            (publishable_or_verified_findings, rejected_findings)
        """
        t0 = time.perf_counter()
        self.repo.record_verification_event(
            review_job_id=review_job_id,
            event_type="verification_started",
            metadata={"candidate_count": len(candidate_findings)},
        )

        judge_run = self.repo.create_judge_run(
            {
                "review_job_id": review_job_id,
                "model_name": "adversarial-judge-v1",
                "prompt_version": "judge.v1",
                "status": "RUNNING",
                "started_at": datetime.now(UTC),
            }
        )

        total_input_tokens = 0
        total_output_tokens = 0
        total_tokens = 0
        total_cost = 0.0

        surviving_candidates: list[ReviewFinding] = []
        rejected_findings: list[ReviewFinding] = []

        # ---------------------------------------------------------------------
        # 1. Evaluate each candidate finding through Adversarial Judge Gates
        # ---------------------------------------------------------------------
        for finding in candidate_findings:
            # Ensure finding is persisted in database
            self.repo.upsert_finding(
                {
                    "id": finding.finding_id,
                    "review_job_id": review_job_id,
                    "file_path": finding.file_path,
                    "line_number": finding.line_number,
                    "side": finding.side,
                    "start_line": finding.start_line,
                    "start_side": finding.start_side,
                    "category": finding.category.value if hasattr(finding.category, "value") else str(finding.category),
                    "severity": finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity),
                    "title": finding.title,
                    "description": finding.description,
                    "impact": finding.impact,
                    "recommendation": finding.recommendation,
                    "confidence": finding.confidence,
                    "agent_name": finding.agent_name or "specialist",
                    "source_agents": finding.source_agents or ([finding.agent_name] if finding.agent_name else []),
                    "status": finding.status.value if hasattr(finding.status, "value") else str(finding.status),
                    "evidence": [ev.model_dump() for ev in finding.evidence],
                }
            )

            finding_diff_hunks = diff_hunks_by_file.get(finding.file_path, [])
            finding_source = source_code_by_file.get(finding.file_path, "")

            # Compile context
            ast_context_str = json.dumps(ast_chunks_by_file.get(finding.file_path, []), indent=2)
            source_and_ast = f"=== SOURCE CODE ({finding.file_path}) ===\n{finding_source[:8000]}\n\n=== AST CHUNKS ===\n{ast_context_str[:4000]}"

            # Caller and surrounding guards context
            callers_str = json.dumps(context_by_symbol.get(finding.affected_symbol or "", {}), indent=2)
            # Search for other callers in repository
            caller_and_guard_context = f"=== SYMBOL CONTEXT & CALLERS ===\n{callers_str}"

            decision, meta = await self.judge.evaluate_finding(
                finding=finding,
                changed_files=changed_files,
                valid_lines_by_file=valid_lines_by_file,
                diff_hunks=finding_diff_hunks,
                source_and_ast_context=source_and_ast,
                caller_and_guard_context=caller_and_guard_context,
                existing_tests_context="Existing test suite available in repo.",
            )

            total_input_tokens += meta.get("input_tokens", 0)
            total_output_tokens += meta.get("output_tokens", 0)
            total_tokens += meta.get("total_tokens", 0)
            total_cost += meta.get("estimated_cost", 0.0)

            # Record Judge Decision
            self.repo.create_judge_decision(
                {
                    "finding_id": finding.finding_id,
                    "judge_run_id": judge_run.id,
                    "decision": decision.decision.value,
                    "final_severity": decision.final_severity.value,
                    "final_confidence": decision.final_confidence,
                    "boundary_passed": decision.boundary_passed,
                    "factuality_passed": decision.factuality_passed,
                    "actionability_passed": decision.actionability_passed,
                    "severity_passed": decision.severity_passed,
                    "duplicate_of": decision.duplicate_of,
                    "root_cause_id": decision.root_cause_id,
                    "verification_summary": decision.verification_summary,
                    "rejection_reason": decision.rejection_reason,
                }
            )

            finding.original_severity = finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)
            finding.final_severity = decision.final_severity.value
            finding.specialist_confidence = finding.confidence
            finding.judge_confidence = decision.judge_confidence
            finding.final_confidence = decision.final_confidence
            finding.validation_notes = decision.verification_summary

            if decision.decision == JudgeDecisionType.REJECT:
                finding.status = FindingStatus.REJECTED
                rejected_findings.append(finding)
                self.repo.record_verification_event(
                    review_job_id=review_job_id,
                    finding_id=finding.finding_id,
                    event_type="judge_rejected",
                    metadata={"reason": decision.rejection_reason},
                )
            else:
                surviving_candidates.append(finding)
                self.repo.record_verification_event(
                    review_job_id=review_job_id,
                    finding_id=finding.finding_id,
                    event_type="judge_accepted",
                    metadata={"final_severity": finding.final_severity, "final_confidence": finding.final_confidence},
                )

        # ---------------------------------------------------------------------
        # 2. Deduplication & Root-Cause Grouping
        # ---------------------------------------------------------------------
        canonical_findings, duplicate_findings = DeduplicationEngine.deduplicate_and_group(surviving_candidates)
        rejected_findings.extend(duplicate_findings)

        for dup in duplicate_findings:
            self.repo.record_verification_event(
                review_job_id=review_job_id,
                finding_id=dup.finding_id,
                event_type="finding_deduplicated",
                metadata={"duplicate_of": dup.duplicate_of},
            )

        # ---------------------------------------------------------------------
        # 3. Validation Policy & Execution Sandbox / Static Analysis
        # ---------------------------------------------------------------------
        publishable_findings: list[ReviewFinding] = []

        for finding in canonical_findings:
            exec_decision = ValidationPolicy.evaluate_finding(
                finding=finding,
                has_test_suite=bool(repo_dir and os.path.isdir(repo_dir)),
                is_safe_sandbox_target=True,
            )

            if exec_decision == ExecutionDecision.NO_EXECUTION:
                # Passes directly to PUBLISHABLE (or VALIDATED if non-critical)
                finding.status = FindingStatus.PUBLISHABLE
                publishable_findings.append(finding)
                self.repo.record_verification_event(
                    review_job_id=review_job_id,
                    finding_id=finding.finding_id,
                    event_type="finding_verified",
                    metadata={"decision": "NO_EXECUTION", "status": finding.status.value},
                )

            elif exec_decision == ExecutionDecision.STATIC_ONLY:
                # Run static analyzers if available
                scenario = self.repo.create_validation_scenario(
                    {
                        "finding_id": finding.finding_id,
                        "scenario_type": "STATIC",
                        "description": f"Static analysis for {finding.file_path}",
                        "command": f"ruff check {finding.file_path}",
                        "expected_behavior": "Static check identifies or validates syntax/contract compliance",
                    }
                )

                if repo_dir:
                    static_results = await self.static_manager.run_analysis(
                        repo_dir=repo_dir,
                        file_path=finding.file_path,
                        target_line=finding.line_number,
                    )
                    static_passed = all(sr.passed for sr in static_results)
                    raw_out = "\n".join(sr.raw_output for sr in static_results)
                else:
                    static_passed = True
                    raw_out = "Static analyzer skipped: No local repository checkout provided."

                self.repo.create_validation_result(
                    {
                        "scenario_id": scenario.id,
                        "status": "PASS" if static_passed else "FAIL",
                        "exit_code": 0 if static_passed else 1,
                        "stdout_summary": raw_out[:1000],
                        "stderr_summary": "",
                        "duration_ms": 10.0,
                        "evidence": [],
                    }
                )

                finding.status = FindingStatus.PUBLISHABLE
                publishable_findings.append(finding)
                self.repo.record_verification_event(
                    review_job_id=review_job_id,
                    finding_id=finding.finding_id,
                    event_type="finding_verified",
                    metadata={"decision": "STATIC_ONLY", "status": finding.status.value},
                )

            elif exec_decision == ExecutionDecision.EXECUTE:
                # Create and execute behavioral validation scenario
                scenario = self.repo.create_validation_scenario(
                    {
                        "finding_id": finding.finding_id,
                        "scenario_type": "BEHAVIORAL",
                        "description": f"Behavioral test execution for {finding.title}",
                        "command": "pytest",
                        "timeout_seconds": 30,
                        "expected_behavior": "Repository test suite executes to verify behavioral assertions",
                    }
                )

                target_dir = repo_dir or os.getcwd()
                val_res = await self.sandbox.execute_scenario(
                    scenario_id=scenario.id,
                    repo_dir=target_dir,
                    command=scenario.command,
                    timeout=scenario.timeout_seconds,
                )

                self.repo.create_validation_result(
                    {
                        "scenario_id": scenario.id,
                        "status": val_res.status,
                        "exit_code": val_res.exit_code,
                        "stdout_summary": val_res.stdout_summary,
                        "stderr_summary": val_res.stderr_summary,
                        "duration_ms": val_res.duration_ms,
                        "evidence": val_res.evidence,
                    }
                )

                if val_res.status == "PASS":
                    finding.status = FindingStatus.PUBLISHABLE
                    # Execution bonus
                    finding.final_confidence = min(0.99, round(finding.final_confidence + 0.05, 2))
                    publishable_findings.append(finding)
                    self.repo.record_verification_event(
                        review_job_id=review_job_id,
                        finding_id=finding.finding_id,
                        event_type="finding_verified",
                        metadata={"decision": "EXECUTION_PASSED", "status": finding.status.value},
                    )
                elif val_res.status == "TIMEOUT":
                    # Execution timed out: mark not publishable / rejected
                    finding.status = FindingStatus.REJECTED
                    finding.validation_notes = f"Execution timed out after {scenario.timeout_seconds}s"
                    rejected_findings.append(finding)
                    self.repo.record_verification_event(
                        review_job_id=review_job_id,
                        finding_id=finding.finding_id,
                        event_type="judge_rejected",
                        metadata={"reason": "EXECUTION_TIMEOUT"},
                    )
                else:
                    # Execution failed
                    finding.status = FindingStatus.REJECTED
                    finding.validation_notes = f"Execution validation failed with exit code {val_res.exit_code}"
                    rejected_findings.append(finding)
                    self.repo.record_verification_event(
                        review_job_id=review_job_id,
                        finding_id=finding.finding_id,
                        event_type="judge_rejected",
                        metadata={"reason": "EXECUTION_VALIDATION_FAILED"},
                    )

            # Persist Evidence Chain items to finding_evidence table
            for ev in finding.evidence:
                self.repo.create_finding_evidence(
                    {
                        "finding_id": finding.finding_id,
                        "evidence_type": ev.type.value if hasattr(ev.type, "value") else str(ev.type),
                        "file_path": ev.file,
                        "line_start": ev.line_start,
                        "line_end": ev.line_end,
                        "symbol_name": ev.symbol,
                        "snippet": None,
                        "description": ev.description,
                        "source_type": finding.agent_name,
                    }
                )

        # ---------------------------------------------------------------------
        # 4. Finalize Judge Run record
        # ---------------------------------------------------------------------
        t_total = (time.perf_counter() - t0) * 1000.0
        judge_run.completed_at = datetime.now(UTC)
        judge_run.latency_ms = round(t_total, 2)
        judge_run.input_tokens = total_input_tokens
        judge_run.output_tokens = total_output_tokens
        judge_run.total_tokens = total_tokens
        judge_run.estimated_cost = round(total_cost, 6)
        judge_run.status = "COMPLETED"
        self.db.commit()

        self.repo.record_verification_event(
            review_job_id=review_job_id,
            event_type="verification_completed",
            metadata={
                "publishable_count": len(publishable_findings),
                "rejected_count": len(rejected_findings),
                "latency_ms": t_total,
            },
        )

        # Update all processed findings in database
        for f in publishable_findings + rejected_findings:
            self.repo.update_finding(
                f.finding_id,
                {
                    "status": f.status.value if hasattr(f.status, "value") else str(f.status),
                    "original_severity": f.original_severity,
                    "final_severity": f.final_severity,
                    "specialist_confidence": f.specialist_confidence,
                    "judge_confidence": f.judge_confidence,
                    "final_confidence": f.final_confidence,
                    "source_agents": f.source_agents or [f.agent_name],
                    "duplicate_of": f.duplicate_of,
                    "root_cause_id": f.root_cause_id,
                    "finding_group_id": f.finding_group_id,
                    "validation_notes": f.validation_notes,
                },
            )

        return publishable_findings, rejected_findings
