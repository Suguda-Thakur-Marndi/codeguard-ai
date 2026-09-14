"""Database repository for Phase 3 & Phase 4 ReviewFindings, AgentRuns, Judge, and Validation records."""

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.models.agent_run import AgentRun
from app.models.agent_trace import AgentTrace
from app.models.finding_evidence import FindingEvidenceModel
from app.models.judge_decision import JudgeDecisionModel
from app.models.judge_run import JudgeRun
from app.models.review_finding import ReviewFindingModel
from app.models.validation_result import ValidationResultModel
from app.models.validation_scenario import ValidationScenarioModel
from app.models.verification_event import VerificationEventModel


class ReviewFindingRepository:
    """Repository handling persistence and queries for review findings, judge runs, validation scenarios, and audit trails."""

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # Findings
    # -------------------------------------------------------------------------
    def create_finding(self, finding_data: dict[str, Any]) -> ReviewFindingModel:
        finding = ReviewFindingModel(**finding_data)
        self.db.add(finding)
        self.db.commit()
        self.db.refresh(finding)
        return finding

    def upsert_finding(self, finding_data: dict[str, Any]) -> ReviewFindingModel:
        finding_id = finding_data.get("id")
        if finding_id:
            existing = self.get_finding(finding_id)
            if existing:
                for k, v in finding_data.items():
                    if k != "id":
                        setattr(existing, k, v)
                self.db.commit()
                self.db.refresh(existing)
                return existing
        return self.create_finding(finding_data)

    def create_findings_batch(self, findings_data: list[dict[str, Any]]) -> list[ReviewFindingModel]:
        models = [ReviewFindingModel(**d) for d in findings_data]
        self.db.add_all(models)
        self.db.commit()
        for m in models:
            self.db.refresh(m)
        return models

    def update_finding(self, finding_id: str, updates: dict[str, Any]) -> ReviewFindingModel | None:
        finding = self.get_finding(finding_id)
        if not finding:
            return None
        for k, v in updates.items():
            setattr(finding, k, v)
        self.db.commit()
        self.db.refresh(finding)
        return finding

    def get_finding(self, finding_id: str) -> ReviewFindingModel | None:
        stmt = (
            select(ReviewFindingModel)
            .options(
                selectinload(ReviewFindingModel.judge_decisions),
                selectinload(ReviewFindingModel.validation_scenarios).selectinload(ValidationScenarioModel.results),
                selectinload(ReviewFindingModel.grounding_evidence),
            )
            .where(ReviewFindingModel.id == finding_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_findings(
        self,
        review_job_id: str,
        severity: str | None = None,
        category: str | None = None,
        status: str | None = None,
    ) -> list[ReviewFindingModel]:
        stmt = (
            select(ReviewFindingModel)
            .options(
                selectinload(ReviewFindingModel.judge_decisions),
                selectinload(ReviewFindingModel.validation_scenarios).selectinload(ValidationScenarioModel.results),
                selectinload(ReviewFindingModel.grounding_evidence),
            )
            .where(ReviewFindingModel.review_job_id == review_job_id)
        )
        if severity:
            stmt = stmt.where(ReviewFindingModel.severity == severity.upper())
        if category:
            stmt = stmt.where(ReviewFindingModel.category == category.upper())
        if status:
            stmt = stmt.where(ReviewFindingModel.status == status.upper())
        stmt = stmt.order_by(desc(ReviewFindingModel.created_at))
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Agent Runs
    # -------------------------------------------------------------------------
    def create_agent_run(self, run_data: dict[str, Any]) -> AgentRun:
        run = AgentRun(**run_data)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def create_agent_runs_batch(self, runs_data: list[dict[str, Any]]) -> list[AgentRun]:
        models = [AgentRun(**d) for d in runs_data]
        self.db.add_all(models)
        self.db.commit()
        for m in models:
            self.db.refresh(m)
        return models

    def list_agent_runs(self, review_job_id: str) -> list[AgentRun]:
        stmt = select(AgentRun).where(AgentRun.review_job_id == review_job_id).order_by(AgentRun.started_at)
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Agent Traces
    # -------------------------------------------------------------------------
    def create_agent_trace(self, trace_data: dict[str, Any]) -> AgentTrace:
        trace = AgentTrace(**trace_data)
        self.db.add(trace)
        self.db.commit()
        self.db.refresh(trace)
        return trace

    def create_agent_traces_batch(self, traces_data: list[dict[str, Any]]) -> list[AgentTrace]:
        models = [AgentTrace(**d) for d in traces_data]
        self.db.add_all(models)
        self.db.commit()
        for m in models:
            self.db.refresh(m)
        return models

    def list_agent_traces(self, review_job_id: str) -> list[AgentTrace]:
        stmt = select(AgentTrace).where(AgentTrace.review_job_id == review_job_id).order_by(AgentTrace.start_time)
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Judge Runs & Decisions
    # -------------------------------------------------------------------------
    def create_judge_run(self, run_data: dict[str, Any]) -> JudgeRun:
        run = JudgeRun(**run_data)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_judge_run(self, judge_run_id: str) -> JudgeRun | None:
        stmt = (
            select(JudgeRun)
            .options(selectinload(JudgeRun.decisions))
            .where(JudgeRun.id == judge_run_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_judge_runs(self, review_job_id: str) -> list[JudgeRun]:
        stmt = (
            select(JudgeRun)
            .options(selectinload(JudgeRun.decisions))
            .where(JudgeRun.review_job_id == review_job_id)
            .order_by(JudgeRun.started_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create_judge_decision(self, decision_data: dict[str, Any]) -> JudgeDecisionModel:
        decision = JudgeDecisionModel(**decision_data)
        self.db.add(decision)
        self.db.commit()
        self.db.refresh(decision)
        return decision

    def list_judge_decisions_for_finding(self, finding_id: str) -> list[JudgeDecisionModel]:
        stmt = (
            select(JudgeDecisionModel)
            .where(JudgeDecisionModel.finding_id == finding_id)
            .order_by(desc(JudgeDecisionModel.created_at))
        )
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Validation Scenarios & Results
    # -------------------------------------------------------------------------
    def create_validation_scenario(self, scenario_data: dict[str, Any]) -> ValidationScenarioModel:
        scenario = ValidationScenarioModel(**scenario_data)
        self.db.add(scenario)
        self.db.commit()
        self.db.refresh(scenario)
        return scenario

    def list_validation_scenarios_for_finding(self, finding_id: str) -> list[ValidationScenarioModel]:
        stmt = (
            select(ValidationScenarioModel)
            .options(selectinload(ValidationScenarioModel.results))
            .where(ValidationScenarioModel.finding_id == finding_id)
            .order_by(ValidationScenarioModel.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_validation_scenarios_for_job(self, review_job_id: str) -> list[ValidationScenarioModel]:
        stmt = (
            select(ValidationScenarioModel)
            .join(ReviewFindingModel, ValidationScenarioModel.finding_id == ReviewFindingModel.id)
            .options(selectinload(ValidationScenarioModel.results))
            .where(ReviewFindingModel.review_job_id == review_job_id)
            .order_by(ValidationScenarioModel.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create_validation_result(self, result_data: dict[str, Any]) -> ValidationResultModel:
        result = ValidationResultModel(**result_data)
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    # -------------------------------------------------------------------------
    # Finding Evidence
    # -------------------------------------------------------------------------
    def create_finding_evidence(self, evidence_data: dict[str, Any]) -> FindingEvidenceModel:
        ev = FindingEvidenceModel(**evidence_data)
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        return ev

    def create_finding_evidence_batch(self, evidence_items: list[dict[str, Any]]) -> list[FindingEvidenceModel]:
        models = [FindingEvidenceModel(**d) for d in evidence_items]
        self.db.add_all(models)
        self.db.commit()
        for m in models:
            self.db.refresh(m)
        return models

    def list_evidence_for_finding(self, finding_id: str) -> list[FindingEvidenceModel]:
        stmt = (
            select(FindingEvidenceModel)
            .where(FindingEvidenceModel.finding_id == finding_id)
            .order_by(FindingEvidenceModel.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Verification Events (Audit Trail)
    # -------------------------------------------------------------------------
    def record_verification_event(
        self, review_job_id: str, event_type: str, finding_id: str | None = None, metadata: dict[str, Any] | None = None
    ) -> VerificationEventModel:
        ev = VerificationEventModel(
            review_job_id=review_job_id,
            finding_id=finding_id,
            event_type=event_type,
            metadata_json=metadata or {},
        )
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        return ev

    def list_events_for_job(self, review_job_id: str) -> list[VerificationEventModel]:
        stmt = (
            select(VerificationEventModel)
            .where(VerificationEventModel.review_job_id == review_job_id)
            .order_by(VerificationEventModel.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_events_for_finding(self, finding_id: str) -> list[VerificationEventModel]:
        stmt = (
            select(VerificationEventModel)
            .where(VerificationEventModel.finding_id == finding_id)
            .order_by(VerificationEventModel.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    # -------------------------------------------------------------------------
    # Verification Summary
    # -------------------------------------------------------------------------
    def get_job_verification_summary(self, review_job_id: str) -> dict[str, Any]:
        findings = self.list_findings(review_job_id)
        candidate_count = len(findings)
        verified_count = sum(1 for f in findings if f.status in ("VALIDATED", "EXECUTION_VERIFIED", "PUBLISHABLE"))
        rejected_count = sum(1 for f in findings if f.status == "REJECTED" or f.status == "INVALID")
        needs_validation_count = sum(1 for f in findings if f.status == "CANDIDATE")
        publishable_count = sum(1 for f in findings if f.status == "PUBLISHABLE")

        judge_runs = self.list_judge_runs(review_job_id)
        total_judge_tokens = sum(r.total_tokens for r in judge_runs)
        total_judge_cost = sum(float(r.estimated_cost) for r in judge_runs)

        return {
            "review_job_id": review_job_id,
            "candidate_count": candidate_count,
            "verified_count": verified_count,
            "rejected_count": rejected_count,
            "needs_validation_count": needs_validation_count,
            "publishable_count": publishable_count,
            "judge_runs_count": len(judge_runs),
            "total_judge_tokens": total_judge_tokens,
            "total_judge_cost": round(total_judge_cost, 6),
            "rejection_rate": round(rejected_count / candidate_count, 2) if candidate_count > 0 else 0.0,
        }

    # -------------------------------------------------------------------------
    # Usage & Cost Summaries
    # -------------------------------------------------------------------------
    def get_job_usage_summary(self, review_job_id: str) -> dict[str, Any]:
        runs = self.list_agent_runs(review_job_id)
        total_input = sum(r.input_tokens for r in runs)
        total_output = sum(r.output_tokens for r in runs)
        total_tokens = sum(r.total_tokens for r in runs)
        total_cost = sum(float(r.estimated_cost) for r in runs)
        total_latency = sum(r.latency_ms for r in runs)

        # Include judge runs if any
        judge_runs = self.list_judge_runs(review_job_id)
        for jr in judge_runs:
            total_input += jr.input_tokens
            total_output += jr.output_tokens
            total_tokens += jr.total_tokens
            total_cost += float(jr.estimated_cost)
            total_latency += jr.latency_ms

        return {
            "review_job_id": review_job_id,
            "agent_runs_count": len(runs) + len(judge_runs),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_tokens,
            "estimated_cost": round(total_cost, 6),
            "total_latency_ms": round(total_latency, 2),
            "breakdown_by_agent": [
                {
                    "agent_name": r.agent_name,
                    "model_name": r.model_name,
                    "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                    "input_tokens": r.input_tokens,
                    "output_tokens": r.output_tokens,
                    "total_tokens": r.total_tokens,
                    "estimated_cost": float(r.estimated_cost),
                    "latency_ms": r.latency_ms,
                    "retry_count": r.retry_count,
                }
                for r in runs
            ]
            + [
                {
                    "agent_name": "adversarial_judge",
                    "model_name": jr.model_name,
                    "status": jr.status,
                    "input_tokens": jr.input_tokens,
                    "output_tokens": jr.output_tokens,
                    "total_tokens": jr.total_tokens,
                    "estimated_cost": float(jr.estimated_cost),
                    "latency_ms": jr.latency_ms,
                    "retry_count": 0,
                }
                for jr in judge_runs
            ],
        }
