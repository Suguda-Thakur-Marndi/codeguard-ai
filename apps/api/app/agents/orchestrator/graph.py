"""LangGraph StateGraph review workflow with bounded parallel execution and failure isolation."""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.judge.deduplication import DeduplicationEngine
from app.agents.llm.provider import LLMProvider
from app.agents.orchestrator.router import RiskRouter
from app.agents.orchestrator.validator import FindingValidator
from app.agents.schemas.comprehension import ComprehensionResult
from app.agents.schemas.finding import ReviewFinding
from app.agents.schemas.state import ReviewAgentState
from app.agents.specialists.bug import BugAgent
from app.agents.specialists.comprehension import ComprehensionAgent
from app.agents.specialists.performance import PerformanceAgent
from app.agents.specialists.security import SecurityAgent
from app.agents.specialists.test_agent import TestAgent
from app.core.config import settings
from app.core.logging import logger


class ReviewWorkflowBuilder:
    """Constructs and compiles the LangGraph StateGraph review workflow."""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def build(self) -> Any:
        workflow = StateGraph(ReviewAgentState)  # type: ignore[arg-type]

        # -----------------------------------------------------------------
        # Node 1: Request & Diff Ingestion Validation
        # -----------------------------------------------------------------
        async def validate_request_node(state: ReviewAgentState) -> dict[str, Any]:
            """Validate request metadata, diff presence, and changed-line indexing."""
            job_id = state.get("review_job_id")
            head_sha = state.get("head_sha")
            changed_files = state.get("changed_files", [])
            diff_hunks = state.get("diff_hunks_by_file", {})
            changed_lines = state.get("changed_lines_by_file", {})

            errors: list[dict[str, Any]] = list(state.get("errors", []))

            # Security & Integrity: Required identifiers must be present
            if not job_id or not isinstance(job_id, str):
                msg = "Validation failed: 'review_job_id' is required and must be a valid string."
                logger.error(msg)
                errors.append({"node": "validate_request_node", "error": msg})
                return {
                    "is_terminal_failure": True,
                    "is_empty_diff": False,
                    "execution_status": "FAILED",
                    "errors": errors,
                }

            if not head_sha or not isinstance(head_sha, str):
                msg = "Validation failed: 'head_sha' is required and must be a valid commit SHA string."
                logger.error(msg, extra={"job_id": job_id})
                errors.append({"node": "validate_request_node", "error": msg})
                return {
                    "is_terminal_failure": True,
                    "is_empty_diff": False,
                    "execution_status": "FAILED",
                    "errors": errors,
                }

            # Check if PR diff has no changed files or hunks
            if not changed_files and not diff_hunks:
                logger.info(
                    "Validation: diff is empty (0 changed files, 0 hunks).",
                    extra={"job_id": job_id},
                )
                return {
                    "is_terminal_failure": False,
                    "is_empty_diff": True,
                    "execution_status": "COMPLETED",
                }

            # Validate changed_lines indexing structure
            if not isinstance(changed_lines, dict):
                msg = "Validation failed: 'changed_lines_by_file' must be a dictionary."
                logger.error(msg, extra={"job_id": job_id})
                errors.append({"node": "validate_request_node", "error": msg})
                return {
                    "is_terminal_failure": True,
                    "is_empty_diff": False,
                    "execution_status": "FAILED",
                    "errors": errors,
                }

            logger.info(
                f"Request validated successfully: {len(changed_files)} files, "
                f"{sum(len(h) for h in diff_hunks.values())} hunks.",
                extra={"job_id": job_id},
            )
            return {
                "is_terminal_failure": False,
                "is_empty_diff": False,
                "execution_status": "RUNNING",
            }

        # -----------------------------------------------------------------
        # Node: Terminal Failure Handler
        # -----------------------------------------------------------------
        async def terminal_failure_node(state: ReviewAgentState) -> dict[str, Any]:
            """Handle fatal input or validation errors without calling AI models."""
            job_id = state.get("review_job_id", "unknown")
            errors = state.get("errors", [])
            logger.warning(
                f"LangGraph terminated early due to terminal failure: {errors}",
                extra={"job_id": job_id},
            )
            final_output = {
                "review_job_id": job_id,
                "status": "FAILED",
                "summary": "Review terminated early due to fatal validation errors.",
                "validated_finding_count": 0,
                "invalid_finding_count": 0,
                "deduplicated_count": 0,
                "duplicate_count": 0,
                "specialists_run": [],
                "total_tokens": 0,
                "estimated_cost": 0.0,
                "errors": errors,
            }
            return {
                "execution_status": "FAILED",
                "final_review_output": final_output,
                "validated_findings": [],
                "invalid_findings": [],
                "raw_candidate_findings": [],
                "deduplicated_findings": [],
                "duplicate_findings": [],
            }

        # -----------------------------------------------------------------
        # Node: Empty Diff Handler
        # -----------------------------------------------------------------
        async def empty_diff_node(state: ReviewAgentState) -> dict[str, Any]:
            """Handle empty PR diffs cleanly without calling AI models."""
            job_id = state.get("review_job_id", "unknown")
            logger.info("Empty diff detected; bypassing specialists.", extra={"job_id": job_id})
            fallback_comp = ComprehensionResult(
                intent="Empty Diff",
                summary="No code changes detected in diff.",
                functional_changes=[],
                refactors=[],
                changed_components=[],
                affected_interfaces=[],
                risk_areas=[],
                relevant_symbols=[],
                is_documentation_only=False,
            )
            return {
                "comprehension": fallback_comp,
                "selected_specialists": [],
                "routing_reason": "Empty diff: no specialist analysis required.",
                "raw_candidate_findings": [],
                "deduplicated_findings": [],
                "duplicate_findings": [],
                "validated_findings": [],
                "invalid_findings": [],
                "execution_status": "COMPLETED",
            }

        # -----------------------------------------------------------------
        # Node 2: Comprehension Agent
        # -----------------------------------------------------------------
        async def comprehension_node(state: ReviewAgentState) -> dict[str, Any]:
            logger.info("LangGraph node [comprehension] started.", extra={"job_id": state.get("review_job_id")})
            t0 = time.perf_counter()
            start_dt = datetime.now(UTC)
            agent = ComprehensionAgent(self.provider)

            try:
                result, run_meta = await agent.run(
                    title=state.get("pr_title", ""),
                    description=state.get("pr_description", ""),
                    base_sha=state.get("base_sha", ""),
                    head_sha=state.get("head_sha", ""),
                    diff_hunks_by_file=state.get("diff_hunks_by_file", {}),
                    ast_chunks_by_file=state.get("ast_chunks_by_file", {}),
                    context_by_symbol=state.get("context_by_symbol", {}),
                )
                dur_ms = (time.perf_counter() - t0) * 1000.0
                end_dt = datetime.now(UTC)

                trace = {
                    "node_name": "comprehension_node",
                    "agent_name": "comprehension",
                    "status": "COMPLETED",
                    "start_time": start_dt,
                    "end_time": end_dt,
                    "duration_ms": round(dur_ms, 2),
                    "model_name": run_meta.get("model_name"),
                    "input_tokens": run_meta.get("input_tokens", 0),
                    "output_tokens": run_meta.get("output_tokens", 0),
                    "total_tokens": run_meta.get("total_tokens", 0),
                    "retry_count": run_meta.get("retry_count", 0),
                    "error_message": None,
                }

                return {
                    "comprehension": result,
                    "agent_runs": [run_meta],
                    "agent_traces": [trace],
                    "total_input_tokens": run_meta.get("input_tokens", 0),
                    "total_output_tokens": run_meta.get("output_tokens", 0),
                    "total_tokens": run_meta.get("total_tokens", 0),
                    "estimated_cost": run_meta.get("estimated_cost", 0.0),
                }

            except Exception as exc:
                dur_ms = (time.perf_counter() - t0) * 1000.0
                end_dt = datetime.now(UTC)
                err_msg = f"{exc.__class__.__name__}: {str(exc)}"
                logger.error(f"Comprehension agent failed: {err_msg}", exc_info=True)

                trace = {
                    "node_name": "comprehension_node",
                    "agent_name": "comprehension",
                    "status": "FAILED",
                    "start_time": start_dt,
                    "end_time": end_dt,
                    "duration_ms": round(dur_ms, 2),
                    "model_name": "unknown",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "retry_count": 0,
                    "error_message": err_msg,
                }
                err_record = {"node": "comprehension_node", "error": err_msg}

                fallback_comp = ComprehensionResult(
                    intent="Failed to analyze intent",
                    summary="Comprehension agent encountered an error.",
                    functional_changes=[],
                    refactors=[],
                    changed_components=[],
                    affected_interfaces=[],
                    risk_areas=["Comprehension analysis failed"],
                    relevant_symbols=[],
                )
                return {
                    "comprehension": fallback_comp,
                    "agent_traces": [trace],
                    "errors": [err_record],
                }

        # -----------------------------------------------------------------
        # Node 3: Risk Router
        # -----------------------------------------------------------------
        async def risk_router_node(state: ReviewAgentState) -> dict[str, Any]:
            comp = state.get("comprehension")
            changed_files = state.get("changed_files", [])

            if comp is None:
                comp = ComprehensionResult(
                    intent="Default",
                    summary="Default",
                    functional_changes=[],
                    refactors=[],
                    changed_components=[],
                    affected_interfaces=[],
                    risk_areas=[],
                    relevant_symbols=[],
                )

            selected_specialists, reason = RiskRouter.route(comp, changed_files)
            logger.info(
                f"Risk Router selected specialists {selected_specialists}. Reason: {reason}",
                extra={"job_id": state.get("review_job_id")},
            )
            return {
                "selected_specialists": selected_specialists,
                "routing_reason": reason,
            }

        # -----------------------------------------------------------------
        # Node 4: Parallel Specialists Dispatcher with Failure Isolation
        # -----------------------------------------------------------------
        async def specialists_dispatcher_node(state: ReviewAgentState) -> dict[str, Any]:
            selected = state.get("selected_specialists", [])
            logger.info(f"Dispatching specialist agents: {selected}", extra={"job_id": state.get("review_job_id")})

            if not selected:
                return {
                    "security_findings": [],
                    "bug_findings": [],
                    "test_findings": [],
                    "performance_findings": [],
                    "raw_candidate_findings": [],
                }

            sem = asyncio.Semaphore(settings.AGENT_MAX_CONCURRENCY)

            changed_lines = state.get("changed_lines_by_file", {})
            diff_hunks = state.get("diff_hunks_by_file", {})
            ast_chunks = state.get("ast_chunks_by_file", {})
            source_codes = state.get("source_code_by_file", {})
            context_sym = state.get("context_by_symbol", {})

            agent_map: dict[str, Any] = {
                "security": SecurityAgent(self.provider),
                "bug": BugAgent(self.provider),
                "test": TestAgent(self.provider),
                "performance": PerformanceAgent(self.provider),
            }

            async def run_single_specialist(agent_key: str) -> tuple[str, list[ReviewFinding], dict[str, Any], dict[str, Any], dict[str, Any] | None]:
                async with sem:
                    spec_agent = agent_map.get(agent_key)
                    if not spec_agent:
                        return agent_key, [], {}, {}, {"error": f"Unknown specialist {agent_key}"}

                    t0 = time.perf_counter()
                    start_dt = datetime.now(UTC)
                    try:
                        out, run_meta = await spec_agent.run(
                            changed_lines_by_file=changed_lines,
                            diff_hunks_by_file=diff_hunks,
                            ast_chunks_by_file=ast_chunks,
                            source_code_by_file=source_codes,
                            context_by_symbol=context_sym,
                        )
                        dur_ms = (time.perf_counter() - t0) * 1000.0
                        end_dt = datetime.now(UTC)

                        trace = {
                            "node_name": f"{agent_key}_node",
                            "agent_name": agent_key,
                            "status": "COMPLETED",
                            "start_time": start_dt,
                            "end_time": end_dt,
                            "duration_ms": round(dur_ms, 2),
                            "model_name": run_meta.get("model_name"),
                            "input_tokens": run_meta.get("input_tokens", 0),
                            "output_tokens": run_meta.get("output_tokens", 0),
                            "total_tokens": run_meta.get("total_tokens", 0),
                            "retry_count": run_meta.get("retry_count", 0),
                            "error_message": None,
                        }
                        return agent_key, out.findings, run_meta, trace, None

                    except Exception as exc:
                        dur_ms = (time.perf_counter() - t0) * 1000.0
                        end_dt = datetime.now(UTC)
                        err_msg = f"{exc.__class__.__name__}: {str(exc)}"
                        logger.error(f"Specialist agent '{agent_key}' failed (isolated): {err_msg}", exc_info=True)

                        run_meta = {
                            "agent_name": agent_key,
                            "agent_version": "1.0.0",
                            "prompt_version": f"{agent_key}.v1",
                            "model_name": "unknown",
                            "status": "FAILED",
                            "started_at": start_dt,
                            "completed_at": end_dt,
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                            "estimated_cost": 0.0,
                            "latency_ms": round(dur_ms, 2),
                            "retry_count": 0,
                            "error_message": err_msg,
                        }
                        trace = {
                            "node_name": f"{agent_key}_node",
                            "agent_name": agent_key,
                            "status": "FAILED",
                            "start_time": start_dt,
                            "end_time": end_dt,
                            "duration_ms": round(dur_ms, 2),
                            "model_name": "unknown",
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                            "retry_count": 0,
                            "error_message": err_msg,
                        }
                        err_record = {"agent": agent_key, "error": err_msg}
                        return agent_key, [], run_meta, trace, err_record

            tasks = [run_single_specialist(agent_key) for agent_key in selected]
            results = await asyncio.gather(*tasks)

            sec_findings: list[ReviewFinding] = []
            bug_findings: list[ReviewFinding] = []
            test_findings: list[ReviewFinding] = []
            perf_findings: list[ReviewFinding] = []
            all_runs = list(state.get("agent_runs", []))
            all_traces = list(state.get("agent_traces", []))
            all_errors = list(state.get("errors", []))

            add_in_tokens = 0
            add_out_tokens = 0
            add_tot_tokens = 0
            add_cost = 0.0

            for agent_key, findings, run_meta, trace, err in results:
                if agent_key == "security":
                    sec_findings.extend(findings)
                elif agent_key == "bug":
                    bug_findings.extend(findings)
                elif agent_key == "test":
                    test_findings.extend(findings)
                elif agent_key == "performance":
                    perf_findings.extend(findings)

                if run_meta:
                    all_runs.append(run_meta)
                    add_in_tokens += run_meta.get("input_tokens", 0)
                    add_out_tokens += run_meta.get("output_tokens", 0)
                    add_tot_tokens += run_meta.get("total_tokens", 0)
                    add_cost += run_meta.get("estimated_cost", 0.0)
                if trace:
                    all_traces.append(trace)
                if err:
                    all_errors.append(err)

            return {
                "security_findings": sec_findings,
                "bug_findings": bug_findings,
                "test_findings": test_findings,
                "performance_findings": perf_findings,
                "agent_runs": all_runs,
                "agent_traces": all_traces,
                "errors": all_errors,
                "total_input_tokens": state.get("total_input_tokens", 0) + add_in_tokens,
                "total_output_tokens": state.get("total_output_tokens", 0) + add_out_tokens,
                "total_tokens": state.get("total_tokens", 0) + add_tot_tokens,
                "estimated_cost": round(state.get("estimated_cost", 0.0) + add_cost, 6),
            }

        # -----------------------------------------------------------------
        # Node 5: Finding Aggregation & Deduplication
        # -----------------------------------------------------------------
        async def finding_aggregation_node(state: ReviewAgentState) -> dict[str, Any]:
            all_findings: list[ReviewFinding] = []
            all_findings.extend(state.get("security_findings", []))
            all_findings.extend(state.get("bug_findings", []))
            all_findings.extend(state.get("test_findings", []))
            all_findings.extend(state.get("performance_findings", []))

            # Deterministic deduplication and root-cause grouping
            canonical, duplicates = DeduplicationEngine.deduplicate_and_group(all_findings)
            logger.info(
                f"Aggregated {len(all_findings)} findings -> {len(canonical)} canonical, {len(duplicates)} duplicates.",
                extra={"job_id": state.get("review_job_id")},
            )

            return {
                "raw_candidate_findings": all_findings,
                "deduplicated_findings": canonical,
                "duplicate_findings": duplicates,
            }

        # -----------------------------------------------------------------
        # Node 6: Deterministic Line & Diff Validator
        # -----------------------------------------------------------------
        async def validator_node(state: ReviewAgentState) -> dict[str, Any]:
            canonical_findings = state.get("deduplicated_findings", [])
            changed_files = state.get("changed_files", [])
            changed_lines = state.get("changed_lines_by_file", {})

            validated, invalid = FindingValidator.validate_findings(
                findings=canonical_findings,
                changed_files=changed_files,
                changed_lines_by_file=changed_lines,
            )

            # Determine execution status: PARTIAL if errors occurred, otherwise COMPLETED
            errors = state.get("errors", [])
            execution_status = "PARTIAL" if errors else "COMPLETED"

            logger.info(
                f"Validation finished: {len(validated)} valid findings, {len(invalid)} invalid findings. Status: {execution_status}",
                extra={"job_id": state.get("review_job_id")},
            )

            return {
                "validated_findings": validated,
                "invalid_findings": invalid,
                "execution_status": execution_status,
            }

        # -----------------------------------------------------------------
        # Node 7: Final Structured Review Output
        # -----------------------------------------------------------------
        async def final_review_output_node(state: ReviewAgentState) -> dict[str, Any]:
            job_id = state.get("review_job_id", "")
            comp = state.get("comprehension")
            exec_status = state.get("execution_status", "COMPLETED")

            summary = (
                comp.summary
                if comp and comp.summary
                else ("Review completed successfully." if exec_status == "COMPLETED" else "Review completed with partial warnings.")
            )

            final_output: dict[str, Any] = {
                "review_job_id": job_id,
                "status": exec_status,
                "summary": summary,
                "validated_finding_count": len(state.get("validated_findings", [])),
                "invalid_finding_count": len(state.get("invalid_findings", [])),
                "deduplicated_count": len(state.get("deduplicated_findings", [])),
                "duplicate_count": len(state.get("duplicate_findings", [])),
                "specialists_run": [r.get("agent_name") for r in state.get("agent_runs", [])],
                "total_tokens": state.get("total_tokens", 0),
                "estimated_cost": state.get("estimated_cost", 0.0),
                "errors": state.get("errors", []),
            }

            return {
                "final_review_output": final_output,
            }

        # -----------------------------------------------------------------
        # Conditional Routing Functions
        # -----------------------------------------------------------------
        def route_after_validation(state: ReviewAgentState) -> str:
            if state.get("is_terminal_failure"):
                return "terminal_failure_node"
            if state.get("is_empty_diff"):
                return "empty_diff_node"
            return "comprehension_node"

        def route_after_router(state: ReviewAgentState) -> str:
            selected = state.get("selected_specialists", [])
            if selected:
                return "specialists_dispatcher_node"
            return "finding_aggregation_node"

        # -----------------------------------------------------------------
        # Build Workflow Graph
        # -----------------------------------------------------------------
        workflow.add_node("validate_request_node", validate_request_node)
        workflow.add_node("terminal_failure_node", terminal_failure_node)
        workflow.add_node("empty_diff_node", empty_diff_node)
        workflow.add_node("comprehension_node", comprehension_node)
        workflow.add_node("risk_router_node", risk_router_node)
        workflow.add_node("specialists_dispatcher_node", specialists_dispatcher_node)
        workflow.add_node("finding_aggregation_node", finding_aggregation_node)
        workflow.add_node("validator_node", validator_node)
        workflow.add_node("final_review_output_node", final_review_output_node)

        # Graph Edges
        workflow.add_edge(START, "validate_request_node")

        workflow.add_conditional_edges(
            "validate_request_node",
            route_after_validation,
            {
                "terminal_failure_node": "terminal_failure_node",
                "empty_diff_node": "empty_diff_node",
                "comprehension_node": "comprehension_node",
            },
        )

        workflow.add_edge("terminal_failure_node", END)
        workflow.add_edge("empty_diff_node", "final_review_output_node")
        workflow.add_edge("comprehension_node", "risk_router_node")

        workflow.add_conditional_edges(
            "risk_router_node",
            route_after_router,
            {
                "specialists_dispatcher_node": "specialists_dispatcher_node",
                "finding_aggregation_node": "finding_aggregation_node",
            },
        )

        workflow.add_edge("specialists_dispatcher_node", "finding_aggregation_node")
        workflow.add_edge("finding_aggregation_node", "validator_node")
        workflow.add_edge("validator_node", "final_review_output_node")
        workflow.add_edge("final_review_output_node", END)

        return workflow.compile()
