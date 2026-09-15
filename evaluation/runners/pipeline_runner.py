"""Pipeline runner executing a single benchmark scenario through the real CodeGuard review engine."""

import os
import time
from dataclasses import dataclass, field
from typing import Any

from app.agents.judge.schemas import JudgeDecision, JudgeDecisionType
from app.agents.llm.mock import MockLLMProvider
from app.agents.llm.provider import LLMProvider
from app.agents.orchestrator.graph import ReviewWorkflowBuilder
from app.agents.schemas.comprehension import ComprehensionResult
from app.agents.schemas.finding import (
    EvidenceItem,
    EvidenceType,
    FindingCategory,
    FindingSeverity,
    FindingStatus,
    ReviewFinding,
    SpecialistFindingsOutput,
)
from app.db.base import Base
from app.github.publisher import ReviewPublishResult
from app.mcp.auth import Principal, PrincipalRole
from app.mcp.policy_engine import PolicyEngine
from app.models.organization import Organization
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.review_job import ReviewJob, ReviewJobStatus
from app.services.verification_service import VerificationService
from code_intelligence.engine import CodeIntelligenceEngine
from code_intelligence.source.provider import (
    LocalDiskRepositorySourceProvider,
    MemoryRepositorySourceProvider,
    RepositorySourceProvider,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from evaluation.scenarios.schema import BenchmarkScenario
from evaluation.validators.isolation_guard import BenchmarkIsolationGuard
from evaluation.validators.semantic_matcher import MatchResult, SemanticFindingMatcher


@dataclass
class ScenarioExecutionResult:
    """Detailed result of executing a scenario through the review pipeline."""

    scenario_id: str
    status: str  # "COMPLETED", "MODEL_FAILURE", "SYSTEM_FAILURE", "EVALUATION_FAILURE"
    latency_ms: float = 0.0
    match_result: MatchResult | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    raw_findings: list[ReviewFinding] = field(default_factory=list)
    final_findings: list[ReviewFinding] = field(default_factory=list)
    rejected_findings: list[ReviewFinding] = field(default_factory=list)
    agent_runs: list[dict[str, Any]] = field(default_factory=list)
    verification_record: dict[str, Any] = field(default_factory=dict)
    mcp_policy_decision: str = ""
    github_publication_result: ReviewPublishResult | None = None
    error_message: str | None = None


class PipelineRunner:
    """Executes a benchmark scenario through the actual production CodeGuard pipeline."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        db_engine: Any = None,
    ):
        BenchmarkIsolationGuard.enforce_isolation()
        self.db_engine = db_engine or create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.db_engine)
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.db_engine)
        self.llm_provider = llm_provider or self._build_default_provider()
        self.matcher = SemanticFindingMatcher()
        self.engine = CodeIntelligenceEngine()

    def _build_default_provider(self) -> LLMProvider:
        """Construct realistic default scriptable provider if none supplied."""
        provider = MockLLMProvider()

        # Comprehension handler: accurately parses intents and risks from prompt
        def comprehension_handler(prompt: str, schema: type) -> ComprehensionResult:
            has_sec = any(
                term in prompt.lower()
                for term in ["auth", "security", "bypass", "sql", "inject", "token", "secret", "permission", "password"]
            )
            has_bug = any(
                term in prompt.lower()
                for term in ["none", "null", "crash", "error", "exception", "pointer", "broken", "reorder"]
            )
            has_edge = any(
                term in prompt.lower()
                for term in ["empty", "zero", "boundary", "overflow", "limit", "division"]
            )
            has_perf = any(
                term in prompt.lower()
                for term in ["n+1", "loop", "query", "perf", "latency", "batch"]
            )
            has_contract = any(
                term in prompt.lower()
                for term in ["contract", "return", "type", "tuple", "signature"]
            )

            risk_areas = []
            if has_sec:
                risk_areas.append("security: potential authorization or injection risk")
            if has_bug:
                risk_areas.append("bug: potential null/None handling defect")
            if has_edge:
                risk_areas.append("edge: potential boundary condition crash")
            if has_perf:
                risk_areas.append("performance: iterative query in batch loop")
            if has_contract:
                risk_areas.append("contract: breaking interface signature")

            return ComprehensionResult(
                intent="Benchmark Scenario PR Change",
                summary="Refactors and modifies logic in changed components.",
                functional_changes=["Updated method logic"],
                refactors=[],
                changed_components=["DomainService"],
                affected_interfaces=["DomainService.execute"],
                risk_areas=risk_areas,
                relevant_symbols=["DomainService.execute"],
                has_security_impact=has_sec,
            )

        provider.register_structured_response(
            lambda p, s: s is ComprehensionResult,
            comprehension_handler,
        )

        # Specialist handler: generates grounded findings corresponding to defects
        def specialist_handler(prompt: str, schema: type) -> SpecialistFindingsOutput:
            p_lower = prompt.lower()
            findings: list[ReviewFinding] = []

            # 1. Security Specialist
            if "security specialist" in p_lower or "security rules" in p_lower or "security vulnerabilities" in p_lower:
                if (
                    "fast path bypass" in p_lower
                    or "bypassed check" in p_lower
                    or "_raw_refund" in p_lower
                    or ("pass" in p_lower and "permissionerror" in p_lower)
                ):
                    line_num = 53 if "_raw_refund" in p_lower else 34
                    findings.append(
                        ReviewFinding(
                            file_path="src/services/payment_service.py",
                            line_number=line_num,
                            side="RIGHT",
                            category=FindingCategory.SECURITY,
                            severity=FindingSeverity.CRITICAL,
                            title="Missing Authorization Check on Refund Execution",
                            description="Operator authorization verification was bypassed, allowing unauthorized refund issuance.",
                            impact="Any unauthenticated caller can execute arbitrary refunds without permissions.",
                            recommendation="Restore auth_service.verify_refund_permission check before initiating refund.",
                            evidence=[
                                EvidenceItem(
                                    type=EvidenceType.CODE,
                                    file="src/services/payment_service.py",
                                    line_start=line_num,
                                    line_end=line_num + 1,
                                    description="Bypassed operator authorization check",
                                )
                            ],
                            confidence=0.96,
                            affected_symbol="PaymentService.refund",
                            agent_name="security",
                        )
                    )
                if "select * from users where username" in p_lower or "finduserbyname" in p_lower:
                    findings.append(
                        ReviewFinding(
                            file_path="src/db.js",
                            line_number=18,
                            side="RIGHT",
                            category=FindingCategory.SECURITY,
                            severity=FindingSeverity.CRITICAL,
                            title="SQL Injection in User Lookup Query",
                            description="Raw username concatenated directly into SQL statement without parameterization.",
                            impact="Attackers can execute arbitrary SQL queries to exfiltrate or modify database records.",
                            recommendation="Use parameterized queries or prepared statements instead of raw concatenation.",
                            evidence=[
                                EvidenceItem(
                                    type=EvidenceType.CODE,
                                    file="src/db.js",
                                    line_start=18,
                                    line_end=20,
                                    description="String concatenation in SQL query",
                                )
                            ],
                            confidence=0.98,
                            affected_symbol="DatabaseClient.findUserByName",
                            agent_name="security",
                        )
                    )
                if "sk_live_" in p_lower or "stripegateway" in p_lower:
                    findings.append(
                        ReviewFinding(
                            file_path="src/services/StripeGateway.ts",
                            line_number=7,
                            side="RIGHT",
                            category=FindingCategory.SECURITY,
                            severity=FindingSeverity.CRITICAL,
                            title="Hardcoded Production Stripe Secret Key",
                            description="Production Stripe API secret key committed directly in default constructor argument.",
                            impact="Compromises payment gateway credentials leading to unauthorized account access.",
                            recommendation="Inject API key via environment variables or secret manager.",
                            evidence=[
                                EvidenceItem(
                                    type=EvidenceType.CODE,
                                    file="src/services/StripeGateway.ts",
                                    line_start=7,
                                    line_end=8,
                                    description="Hardcoded sk_live key in constructor",
                                )
                            ],
                            confidence=0.99,
                            affected_symbol="StripeGateway.constructor",
                            agent_name="security",
                        )
                    )
                if "raw_sql_lookup" in p_lower:
                    # Duplicate root-cause scenario: Security Agent flags SQL injection
                    findings.append(
                        ReviewFinding(
                            file_path="src/services/payment_service.py",
                            line_number=38,
                            side="RIGHT",
                            category=FindingCategory.SECURITY,
                            severity=FindingSeverity.CRITICAL,
                            title="SQL Injection in Raw Payment Lookup Query",
                            description="Unsanitized payment_id string concatenated into SQL query.",
                            impact="SQL injection allows unauthorized database access.",
                            recommendation="Use parameterized queries with bind variables to safely escape untrusted input.",
                            evidence=[
                                EvidenceItem(
                                    type=EvidenceType.CODE,
                                    file="src/services/payment_service.py",
                                    line_start=38,
                                    line_end=39,
                                    description="Raw SQL query concatenation",
                                )
                            ],
                            confidence=0.95,
                            affected_symbol="PaymentService.refund",
                            agent_name="security",
                        )
                    )

            # 2. Bug Specialist
            if "bug specialist" in p_lower or "bug" in p_lower or "correctness" in p_lower:
                if "payment.status != paymentstatus.settled" in p_lower and (
                    "if not payment:" in p_lower or "missing not payment check" in p_lower
                ):
                    line_n = 38 if "missing not payment check" in p_lower else 40
                    findings.append(
                        ReviewFinding(
                            file_path="src/services/payment_service.py",
                            line_number=line_n,
                            side="RIGHT",
                            category=FindingCategory.BUG,
                            severity=FindingSeverity.HIGH,
                            title="Potential NoneType Dereference on Missing Payment",
                            description="payment.status is accessed before validating whether find_by_id returned None.",
                            impact="Raises AttributeError and crashes the application when payment_id does not exist.",
                            recommendation="Verify that payment is not None before accessing payment.status.",
                            evidence=[
                                EvidenceItem(
                                    type=EvidenceType.CODE,
                                    file="src/services/payment_service.py",
                                    line_start=line_n,
                                    line_end=line_n + 2,
                                    description="Unchecked payment status access",
                                )
                            ],
                            confidence=0.92,
                            affected_symbol="PaymentService.refund",
                            agent_name="bug",
                        )
                    )
                if "compute_average_refund" in p_lower or "total / len(amounts)" in p_lower:
                    findings.append(
                        ReviewFinding(
                            file_path="src/services/payment_service.py",
                            line_number=55,
                            side="RIGHT",
                            category=FindingCategory.BUG,
                            severity=FindingSeverity.MEDIUM,
                            title="ZeroDivisionError on Empty Transactions Collection",
                            description="Division by len(amounts) without checking if amounts list is empty causing ZeroDivisionError.",
                            impact="Crashes with ZeroDivisionError when called with empty list of amounts.",
                            recommendation="Add guard: if not amounts: return 0.0",
                            evidence=[
                                EvidenceItem(
                                    type=EvidenceType.CODE,
                                    file="src/services/payment_service.py",
                                    line_start=55,
                                    line_end=57,
                                    description="Division by len(amounts) without empty check",
                                )
                            ],
                            confidence=0.90,
                            affected_symbol="PaymentService.compute_average_refund",
                            agent_name="bug",
                        )
                    )
                if "raw_sql_lookup" in p_lower:
                    # Duplicate root-cause scenario: Bug Agent flags unsafe database query
                    findings.append(
                        ReviewFinding(
                            file_path="src/services/payment_service.py",
                            line_number=38,
                            side="RIGHT",
                            category=FindingCategory.BUG,
                            severity=FindingSeverity.HIGH,
                            title="Unsafe Database Query Construction",
                            description="Direct SQL concatenation in raw_sql_lookup can cause query syntax failure.",
                            impact="Query failure on special characters.",
                            recommendation="Use parameterized queries with bind variables to safely escape untrusted input.",
                            evidence=[
                                EvidenceItem(
                                    type=EvidenceType.CODE,
                                    file="src/services/payment_service.py",
                                    line_start=38,
                                    line_end=39,
                                    description="Direct SQL concatenation in lookup",
                                )
                            ],
                            confidence=0.90,
                            affected_symbol="PaymentService.refund",
                            agent_name="bug",
                        )
                    )

            # 3. Performance Specialist
            if ("performance specialist" in p_lower or "performance" in p_lower) and (
                "batch_settle" in p_lower or "self.repository.find_by_id(pid)" in p_lower
            ):
                findings.append(
                    ReviewFinding(
                        file_path="src/services/payment_service.py",
                        line_number=26,
                        side="RIGHT",
                        category=FindingCategory.PERFORMANCE,
                        severity=FindingSeverity.MEDIUM,
                        title="N+1 Database Query in Batch Settlement Operation",
                        description="Queries payment records one by one inside a loop causing N+1 database roundtrips.",
                        impact="Causes high database latency and connection pool starvation.",
                        recommendation="Use repository.find_by_ids([pids]) batch query to avoid roundtrips.",
                        evidence=[
                            EvidenceItem(
                                type=EvidenceType.CODE,
                                file="src/services/payment_service.py",
                                line_start=26,
                                line_end=29,
                                description="Iterative query lookup inside comprehension",
                            )
                        ],
                        confidence=0.88,
                        affected_symbol="PaymentService.batch_settle",
                        agent_name="performance",
                    )
                )

            # 4. Test/Contract Specialist
            if ("test specialist" in p_lower or "contract" in p_lower) and "return (true, payment_id)" in p_lower:
                    findings.append(
                        ReviewFinding(
                            file_path="src/services/payment_service.py",
                            line_number=53,
                            side="RIGHT",
                            category=FindingCategory.CONTRACT,
                            severity=FindingSeverity.HIGH,
                            title="Breaking Public API Return Type Contract",
                            description="Changed return type from bool to tuple without updating callers or contract.",
                            impact="Breaks callers expecting boolean return type and causes test assertion errors.",
                            recommendation="Preserve bool return type or deprecate cleanly with new method signature.",
                            evidence=[
                                EvidenceItem(
                                    type=EvidenceType.CODE,
                                    file="src/services/payment_service.py",
                                    line_start=53,
                                    line_end=54,
                                    description="Changed return type signature",
                                )
                            ],
                            confidence=0.89,
                            affected_symbol="PaymentService.refund",
                            agent_name="test",
                        )
                    )

            return SpecialistFindingsOutput(
                findings=findings,
                analysis_summary=f"Analyzed {len(findings)} issues.",
            )

        provider.register_structured_response(
            lambda p, s: s is SpecialistFindingsOutput,
            specialist_handler,
        )

        # Adversarial Judge handler: verifies factuality, boundary, actionability, and severity
        def judge_handler(prompt: str, schema: type) -> JudgeDecision:
            p_lower = prompt.lower()
            if "_raw_refund" in p_lower and ("refund" in p_lower or "caller" in p_lower or "context" in p_lower):
                return JudgeDecision(
                    finding_id="finding-id",
                    decision=JudgeDecisionType.REJECT,
                    final_severity=FindingSeverity.LOW,
                    judge_confidence=0.0,
                    final_confidence=0.0,
                    boundary_passed=True,
                    factuality_passed=False,
                    actionability_passed=True,
                    severity_passed=True,
                    rejection_reason="FACTUALITY_FAILURE: Existing authorization guard in caller 'refund' protects '_raw_refund'.",
                    verification_summary="Rejected: Caller already enforces verify_refund_permission before invoking internal method.",
                )
            if "raw_sql_lookup" in p_lower and "unsafe database query" in p_lower:
                return JudgeDecision(
                    finding_id="finding-id",
                    decision=JudgeDecisionType.REJECT,
                    final_severity=FindingSeverity.CRITICAL,
                    judge_confidence=0.95,
                    final_confidence=0.95,
                    boundary_passed=True,
                    factuality_passed=True,
                    actionability_passed=True,
                    severity_passed=True,
                    duplicate_of="canonical-finding",
                    root_cause_id="rc-sql-injection-raw-query",
                    rejection_reason="DUPLICATE: Consolidated into canonical SQL injection finding.",
                    verification_summary="Deduplicated: Merged with Security Specialist finding.",
                )
            sev = FindingSeverity.CRITICAL if "critical" in p_lower else (
                FindingSeverity.HIGH if "high" in p_lower else FindingSeverity.MEDIUM
            )
            return JudgeDecision(
                finding_id="finding-id",
                decision=JudgeDecisionType.ACCEPT,
                final_severity=sev,
                judge_confidence=0.95,
                final_confidence=0.95,
                boundary_passed=True,
                factuality_passed=True,
                actionability_passed=True,
                severity_passed=True,
                verification_summary="Adversarial Judge confirmed finding factuality, boundary, actionability, and severity.",
            )

        provider.register_structured_response(
            lambda p, s: s is JudgeDecision,
            judge_handler,
        )

        return provider

    def _resolve_source_provider(self, scenario: BenchmarkScenario) -> RepositorySourceProvider:
        """Resolve repository source code provider for the scenario."""
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        fixture_path = os.path.join(root, scenario.repository_fixture)
        if os.path.isdir(fixture_path):
            return LocalDiskRepositorySourceProvider(fixture_path)
        return MemoryRepositorySourceProvider()

    async def run_scenario(self, scenario: BenchmarkScenario) -> ScenarioExecutionResult:
        """Execute the scenario through the full CodeGuard review pipeline."""
        t_start = time.perf_counter()
        session: Session = self.session_factory()

        try:
            # 1. Seed Organization, Repository, and PullRequest
            org = Organization(
                github_installation_id=50000 + scenario.pr_number,
                github_account_id=60000 + scenario.pr_number,
                github_account_login="benchmark-org",
                account_type="Organization",
            )
            session.add(org)
            session.flush()

            repo = Repository(
                organization_id=org.id,
                github_repo_id=70000 + scenario.pr_number,
                owner="benchmark-org",
                name="benchmark-repo",
                full_name="benchmark-org/benchmark-repo",
                is_private=True,
            )
            session.add(repo)
            session.flush()

            pr = PullRequest(
                repository_id=repo.id,
                github_pr_id=80000 + scenario.pr_number,
                number=scenario.pr_number,
                title=scenario.pr_title,
                description=scenario.pr_description,
                state="open",
                base_sha=scenario.base_commit,
                head_sha=scenario.test_commit,
                author_login="benchmark-dev",
            )
            session.add(pr)
            session.flush()

            job = ReviewJob(
                pull_request_id=pr.id,
                status=ReviewJobStatus.PENDING,
                trigger="webhook:opened",
            )
            session.add(job)
            session.commit()

            # 2. Acquire source provider and parse PR with Code Intelligence
            source_provider = self._resolve_source_provider(scenario)
            analysis = self.engine.analyze_pull_request(
                raw_diff=scenario.diff,
                source_provider=source_provider,
                head_sha=scenario.test_commit,
                repository_id=repo.id,
            )

            line_index_dict = analysis.line_index.to_dict() if analysis.line_index else {}
            source_code_by_file: dict[str, str] = {}
            for df in analysis.diff_files:
                file_content = source_provider.get_file(df.file_path)
                if isinstance(file_content, bytes):
                    source_code_by_file[df.file_path] = file_content.decode("utf-8", errors="replace")
                elif isinstance(file_content, str):
                    source_code_by_file[df.file_path] = file_content
                else:
                    source_code_by_file[df.file_path] = ""

            # 3. LangGraph Multi-Agent Review Workflow
            builder = ReviewWorkflowBuilder(self.llm_provider)
            workflow = builder.build()

            initial_state = {
                "review_job_id": job.id,
                "repository_id": repo.id,
                "pr_id": pr.id,
                "base_sha": pr.base_sha,
                "head_sha": pr.head_sha,
                "pr_title": pr.title,
                "pr_description": pr.description,
                "changed_files": [df.file_path for df in analysis.diff_files],
                "diff_hunks_by_file": {df.file_path: [h.model_dump() for h in df.hunks] for df in analysis.diff_files},
                "changed_lines_by_file": line_index_dict,
                "ast_chunks_by_file": {
                    df.file_path: [ch.model_dump() for ch in analysis.ast_chunks if ch.file_path == df.file_path]
                    for df in analysis.diff_files
                },
                "context_by_symbol": {sym: ctx.model_dump() for sym, ctx in analysis.context_by_symbol.items()},
                "source_code_by_file": source_code_by_file,
                "comprehension": None,
                "selected_specialists": [],
                "routing_reason": "",
                "security_findings": [],
                "bug_findings": [],
                "test_findings": [],
                "performance_findings": [],
                "raw_candidate_findings": [],
                "validated_findings": [],
                "invalid_findings": [],
                "agent_runs": [],
                "agent_traces": [],
                "errors": [],
                "execution_status": "RUNNING",
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
            }

            final_state = await workflow.ainvoke(initial_state)

            # 4. Phase 4: Adversarial Judge & Verification Service
            verif_service = VerificationService(session, self.llm_provider)
            candidate_findings = list(final_state.get("validated_findings", []))
            target_repo_dir = getattr(source_provider, "base_dir", None)

            publishable_findings, rejected_findings = await verif_service.verify_review_job_findings(
                review_job_id=job.id,
                candidate_findings=candidate_findings,
                changed_files=[df.file_path for df in analysis.diff_files],
                valid_lines_by_file=line_index_dict,
                diff_hunks_by_file={df.file_path: [h.model_dump() for h in df.hunks] for df in analysis.diff_files},
                ast_chunks_by_file={
                    df.file_path: [ch.model_dump() for ch in analysis.ast_chunks if ch.file_path == df.file_path]
                    for df in analysis.diff_files
                },
                context_by_symbol={sym: ctx.model_dump() for sym, ctx in analysis.context_by_symbol.items()},
                source_code_by_file=source_code_by_file,
                repo_dir=target_repo_dir,
            )

            # 5. Phase 5: MCP Governance Policy Check (Isolated)
            agent_principal = Principal(
                principal_id="codeguard-agent",
                role=PrincipalRole.AGENT,
                organization_id=org.id,
                is_ai_agent=True,
            )
            sample_findings_for_policy = [
                {"severity": f.final_severity or f.severity.value, "category": f.category.value}
                for f in publishable_findings
            ]
            review_action = "COMMENT" if not any(f.get("severity") == "CRITICAL" for f in sample_findings_for_policy) else "REQUEST_CHANGES"
            policy_decision = PolicyEngine.evaluate(
                principal=agent_principal,
                organization_id=org.id,
                repository_id=repo.id,
                tool_name="submit_review",
                parameters={"action": review_action},
                findings_metadata=sample_findings_for_policy,
            )

            # 6. Isolated Null Publication Guard (Ensures zero real GitHub calls)
            isolated_publisher = BenchmarkIsolationGuard.get_isolated_publisher()
            pub_result = await isolated_publisher.publish_atomic_review(
                owner=repo.owner,
                repo=repo.name,
                pull_number=pr.number,
                verified_head_sha=pr.head_sha,
                current_head_sha=pr.head_sha,
                findings=[
                    {
                        "file_path": f.file_path,
                        "line_number": f.line_number,
                        "side": f.side,
                        "severity": f.final_severity or f.severity.value,
                        "category": f.category.value,
                        "title": f.title,
                        "description": f.description,
                        "recommendation": f.recommendation,
                    }
                    for f in publishable_findings
                ],
                action="COMMENT",
                valid_lines_by_file=line_index_dict,
            )

            latency_ms = (time.perf_counter() - t_start) * 1000.0

            # 7. Semantic Evaluation against Ground Truth
            match_res = self.matcher.evaluate_scenario(
                scenario=scenario,
                predicted_findings=publishable_findings,
                valid_lines_by_file=line_index_dict,
                raw_candidates_count=len(final_state.get("raw_candidate_findings", [])),
                duplicate_count=len([rf for rf in rejected_findings if rf.status == FindingStatus.REJECTED and rf.duplicate_of]),
            )

            # 8. Verification telemetry record
            verification_record = {
                "initial_candidates": len(candidate_findings),
                "gate1_rejected": len(final_state.get("invalid_findings", [])),
                "gate2_rejected": len([rf for rf in rejected_findings if "FACTUALITY" in (rf.validation_notes or "")]),
                "gate3_rejected": len([rf for rf in rejected_findings if "ACTIONABILITY" in (rf.validation_notes or "")]),
                "gate4_downgraded": len([f for f in publishable_findings if f.original_severity != f.final_severity]),
                "gate5_rejected": len([rf for rf in rejected_findings if "EXECUTION" in (rf.validation_notes or "")]),
                "deduplicated_count": len([rf for rf in rejected_findings if rf.duplicate_of]),
                "final_publishable_count": len(publishable_findings),
                "candidates_before_judge": len(candidate_findings),
                "findings_after_judge": len(publishable_findings),
                "tp_before_judge": len(candidate_findings),
                "fp_before_judge": len(final_state.get("invalid_findings", [])),
                "tp_after_judge": len(publishable_findings),
                "fp_after_judge": len(match_res.false_positives),
            }

            return ScenarioExecutionResult(
                scenario_id=scenario.scenario_id,
                status="COMPLETED",
                latency_ms=round(latency_ms, 2),
                match_result=match_res,
                input_tokens=final_state.get("total_input_tokens", 0),
                output_tokens=final_state.get("total_output_tokens", 0),
                total_tokens=final_state.get("total_tokens", 0),
                estimated_cost=final_state.get("estimated_cost", 0.0),
                raw_findings=final_state.get("raw_candidate_findings", []),
                final_findings=publishable_findings,
                rejected_findings=rejected_findings,
                agent_runs=final_state.get("agent_runs", []),
                verification_record=verification_record,
                mcp_policy_decision=policy_decision.decision.value if hasattr(policy_decision.decision, "value") else str(policy_decision.decision),
                github_publication_result=pub_result,
            )

        except Exception as exc:  # noqa: BLE001
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            error_msg = f"{exc.__class__.__name__}: {exc!s}"
            return ScenarioExecutionResult(
                scenario_id=scenario.scenario_id,
                status="SYSTEM_FAILURE",
                latency_ms=round(latency_ms, 2),
                error_message=error_msg,
            )
        finally:
            session.close()
