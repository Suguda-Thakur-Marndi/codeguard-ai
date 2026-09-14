"""LangGraph StateGraph review workflow with bounded parallel execution and failure isolation."""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.llm.provider import LLMProvider
from app.agents.orchestrator.router import RiskRouter
from app.agents.orchestrator.validator import FindingValidator
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
        workflow = StateGraph(ReviewAgentState)

        # -----------------------------------------------------------------
        # Node 1: Comprehension Agent
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

                # Fallback comprehension so review can continue with standard defaults
                from app.agents.schemas.comprehension import ComprehensionResult
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
        # Node 2: Risk Router
        # -----------------------------------------------------------------
        async def risk_router_node(state: ReviewAgentState) -> dict[str, Any]:
            comp = state.get("comprehension")
            changed_files = state.get("changed_files", [])

            if comp is None:
                from app.agents.schemas.comprehension import ComprehensionResult
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
        # Node 3: Parallel Specialists Dispatcher with Failure Isolation
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

            # Specialist agent mapping
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

            # Execute specialists concurrently
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
        # Node 4: Finding Collector
        # -----------------------------------------------------------------
        async def finding_collector_node(state: ReviewAgentState) -> dict[str, Any]:
            all_findings = []
            all_findings.extend(state.get("security_findings", []))
            all_findings.extend(state.get("bug_findings", []))
            all_findings.extend(state.get("test_findings", []))
            all_findings.extend(state.get("performance_findings", []))

            logger.info(f"Collector collected {len(all_findings)} raw candidate findings.")
            return {"raw_candidate_findings": all_findings}

        # -----------------------------------------------------------------
        # Node 5: Deterministic Validator
        # -----------------------------------------------------------------
        async def validator_node(state: ReviewAgentState) -> dict[str, Any]:
            raw_findings = state.get("raw_candidate_findings", [])
            changed_files = state.get("changed_files", [])
            changed_lines = state.get("changed_lines_by_file", {})

            validated, invalid = FindingValidator.validate_findings(
                findings=raw_findings,
                changed_files=changed_files,
                changed_lines_by_file=changed_lines,
            )

            # Determine execution status
            errors = state.get("errors", [])
            if errors:
                execution_status = "PARTIAL"
            else:
                execution_status = "COMPLETED"

            logger.info(
                f"Validation finished: {len(validated)} valid findings, {len(invalid)} invalid findings. Status: {execution_status}",
                extra={"job_id": state.get("review_job_id")},
            )

            return {
                "validated_findings": validated,
                "invalid_findings": invalid,
                "execution_status": execution_status,
            }

        # Connect nodes in StateGraph
        workflow.add_node("comprehension_node", comprehension_node)
        workflow.add_node("risk_router_node", risk_router_node)
        workflow.add_node("specialists_dispatcher_node", specialists_dispatcher_node)
        workflow.add_node("finding_collector_node", finding_collector_node)
        workflow.add_node("validator_node", validator_node)

        workflow.add_edge(START, "comprehension_node")
        workflow.add_edge("comprehension_node", "risk_router_node")
        workflow.add_edge("risk_router_node", "specialists_dispatcher_node")
        workflow.add_edge("specialists_dispatcher_node", "finding_collector_node")
        workflow.add_edge("finding_collector_node", "validator_node")
        workflow.add_edge("validator_node", END)

        return workflow.compile()
