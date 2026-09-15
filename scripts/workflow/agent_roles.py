"""Agency Agent role definitions, boundaries, and report schemas."""

from enum import Enum
import re
from typing import Any
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    ARCHITECT = "ARCHITECT AGENT"
    BACKEND = "BACKEND AGENT"
    FRONTEND = "FRONTEND AGENT"
    DATABASE = "DATABASE AGENT"
    SECURITY = "SECURITY AGENT"
    MCP = "MCP AGENT"
    AI_LANGGRAPH = "AI/LANGGRAPH AGENT"
    CODE_INTELLIGENCE = "CODE INTELLIGENCE AGENT"
    TESTING = "TESTING AGENT"
    DEVOPS = "DEVOPS AGENT"
    REVIEW = "REVIEW AGENT"
    FINAL_INTEGRATION = "FINAL INTEGRATION AGENT"


class AgentStatus(str, Enum):
    SUCCESS = "SUCCESS"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"


class RoleDefinition(BaseModel):
    """Configuration and bounded scope for an Agency Agent role."""

    role: AgentRole
    description: str
    allowed_file_patterns: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    requires_approval_for_merge: bool = True


ROLE_REGISTRY: dict[AgentRole, RoleDefinition] = {
    AgentRole.ARCHITECT: RoleDefinition(
        role=AgentRole.ARCHITECT,
        description="Inspects system structure, dependencies, module boundaries, and proposes minimal changes.",
        allowed_file_patterns=["docs/*", "architecture/*", "*.md"],
        forbidden_actions=["broad_redesign", "direct_code_mutation_without_consensus"],
    ),
    AgentRole.BACKEND: RoleDefinition(
        role=AgentRole.BACKEND,
        description="FastAPI routers, business services, authentication, workers, background tasks.",
        allowed_file_patterns=["apps/api/*", "packages/shared/*"],
        forbidden_actions=["ui_redesign", "bypass_api_contracts", "skip_authentication"],
    ),
    AgentRole.FRONTEND: RoleDefinition(
        role=AgentRole.FRONTEND,
        description="Next.js components, API hooks, state handling, loading/error states in existing UI.",
        allowed_file_patterns=["apps/web/*"],
        forbidden_actions=["ui_redesign", "layout_overhaul", "color_palette_change", "backend_edits"],
    ),
    AgentRole.DATABASE: RoleDefinition(
        role=AgentRole.DATABASE,
        description="PostgreSQL models, Alembic migrations, indexes, constraints, transactions.",
        allowed_file_patterns=["apps/api/alembic/*", "apps/api/app/models/*", "apps/api/app/db/*"],
        forbidden_actions=["drop_table_without_migration", "direct_production_db_mutation", "data_loss"],
    ),
    AgentRole.SECURITY: RoleDefinition(
        role=AgentRole.SECURITY,
        description="Zero-trust review: auth, permissions, sandbox, secrets, prompt injection, tenant isolation.",
        allowed_file_patterns=["*"],
        forbidden_actions=["disable_security", "bypass_approval", "hardcode_credentials"],
    ),
    AgentRole.MCP: RoleDefinition(
        role=AgentRole.MCP,
        description="MCP servers, tool schemas, Sentinel policy validation, audit logging, approval integration.",
        allowed_file_patterns=["apps/mcp-server/*", "apps/api/app/mcp/*"],
        forbidden_actions=["bypass_sentinel_policy", "auto_execute_dangerous_tool", "skip_sha_check"],
    ),
    AgentRole.AI_LANGGRAPH: RoleDefinition(
        role=AgentRole.AI_LANGGRAPH,
        description="Gemini provider, LangGraph review workflow, prompt templates, structured output.",
        allowed_file_patterns=["apps/api/app/agents/*"],
        forbidden_actions=["treat_ai_as_authority", "bypass_adversarial_judge", "unconstrained_generation"],
    ),
    AgentRole.CODE_INTELLIGENCE: RoleDefinition(
        role=AgentRole.CODE_INTELLIGENCE,
        description="Tree-sitter AST, diff parsing, symbol indexing, dependency graph, context retrieval.",
        allowed_file_patterns=["packages/code-intelligence/*"],
        forbidden_actions=["replace_treesitter_with_regex", "weaken_diagnostics"],
    ),
    AgentRole.TESTING: RoleDefinition(
        role=AgentRole.TESTING,
        description="Unit, integration, security, benchmark, and regression test suites.",
        allowed_file_patterns=["apps/api/tests/*", "tests/*", "verify_*.py", "evaluation/*"],
        forbidden_actions=["weaken_tests_to_pass", "delete_failing_assertions"],
    ),
    AgentRole.DEVOPS: RoleDefinition(
        role=AgentRole.DEVOPS,
        description="Dockerfiles, docker-compose manifests, health checks, environment configs, CI/CD.",
        allowed_file_patterns=["docker/*", "docker-compose*.yml", "infra/*", ".github/*"],
        forbidden_actions=["commit_secrets", "unnecessary_cloud_restructure"],
    ),
    AgentRole.REVIEW: RoleDefinition(
        role=AgentRole.REVIEW,
        description="Independent quality gate: correctness, security, architecture, maintainability, regressions.",
        allowed_file_patterns=["*"],
        forbidden_actions=["rubber_stamping", "approve_without_verification"],
    ),
    AgentRole.FINAL_INTEGRATION: RoleDefinition(
        role=AgentRole.FINAL_INTEGRATION,
        description="Cross-service verification, import integrity, duplication removal, and end-to-end flow.",
        allowed_file_patterns=["*"],
        forbidden_actions=["skip_integration_tests", "override_security_rejections"],
    ),
}


class TaskInput(BaseModel):
    """Structured task assignment for an Agency Agent."""

    task_id: str
    role: AgentRole
    objective: str
    target_files: list[str] = Field(default_factory=list)
    context_notes: str = ""
    assumptions: list[str] = Field(default_factory=list)


class AgentReport(BaseModel):
    """Structured report produced by an Agency Agent."""

    role: AgentRole
    task: str
    understood_requirement: str
    files_inspected: list[str] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    implementation: str
    tests: str
    security_considerations: str
    risks: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    final_status: AgentStatus = AgentStatus.SUCCESS

    def format_text(self) -> str:
        """Render report into canonical human-readable plain text format."""
        lines = [
            f"ROLE: {self.role.value}",
            f"TASK: {self.task}",
            "",
            "UNDERSTOOD REQUIREMENT:",
            self.understood_requirement,
            "",
            "FILES INSPECTED:",
        ]
        for f in self.files_inspected:
            lines.append(f"- {f}")
        if not self.files_inspected:
            lines.append("- (none)")
        lines.append("")
        lines.append("FILES CHANGED:")
        for f in self.files_changed:
            lines.append(f"- {f}")
        if not self.files_changed:
            lines.append("- (none)")
        lines.append("")
        lines.append("IMPLEMENTATION:")
        lines.append(self.implementation)
        lines.append("")
        lines.append("TESTS:")
        lines.append(self.tests)
        lines.append("")
        lines.append("SECURITY CONSIDERATIONS:")
        lines.append(self.security_considerations)
        lines.append("")
        lines.append("RISKS:")
        for r in self.risks:
            lines.append(f"- {r}")
        if not self.risks:
            lines.append("- (none)")
        lines.append("")
        lines.append("BLOCKERS:")
        for b in self.blockers:
            lines.append(f"- {b}")
        if not self.blockers:
            lines.append("- (none)")
        lines.append("")
        lines.append(f"FINAL STATUS: {self.final_status.value}")
        return "\n".join(lines)


def get_role_definition(role: AgentRole) -> RoleDefinition:
    """Retrieve the bounded role definition."""
    return ROLE_REGISTRY[role]


def parse_agent_report_text(text: str) -> AgentReport:
    """Parse structured text back into an AgentReport model."""
    role_match = re.search(r"ROLE:\s*(.+)", text)
    task_match = re.search(r"TASK:\s*(.+)", text)
    req_match = re.search(r"UNDERSTOOD REQUIREMENT:\s*\n(.*?)(?=\n\nFILES INSPECTED:|\nFILES INSPECTED:)", text, re.DOTALL)
    status_match = re.search(r"FINAL STATUS:\s*([A-Z]+)", text)

    role_val = role_match.group(1).strip() if role_match else AgentRole.ARCHITECT.value
    # Match role enum
    matching_role = AgentRole.ARCHITECT
    for r in AgentRole:
        if r.value.lower() == role_val.lower() or r.name.lower() in role_val.lower():
            matching_role = r
            break

    task_val = task_match.group(1).strip() if task_match else "Unspecified Task"
    req_val = req_match.group(1).strip() if req_match else ""
    status_val = AgentStatus.SUCCESS
    if status_match:
        s_str = status_match.group(1).strip()
        if s_str in AgentStatus._value2member_map_:
            status_val = AgentStatus(s_str)

    # Extract lists
    inspected = re.findall(r"FILES INSPECTED:\s*\n((?:- .*\n?)*)", text)
    inspected_files = [line.strip("- ").strip() for line in inspected[0].splitlines() if line.strip() and "(none)" not in line] if inspected else []

    changed = re.findall(r"FILES CHANGED:\s*\n((?:- .*\n?)*)", text)
    changed_files = [line.strip("- ").strip() for line in changed[0].splitlines() if line.strip() and "(none)" not in line] if changed else []

    impl_match = re.search(r"IMPLEMENTATION:\s*\n(.*?)(?=\n\nTESTS:|\nTESTS:)", text, re.DOTALL)
    tests_match = re.search(r"TESTS:\s*\n(.*?)(?=\n\nSECURITY CONSIDERATIONS:|\nSECURITY CONSIDERATIONS:)", text, re.DOTALL)
    sec_match = re.search(r"SECURITY CONSIDERATIONS:\s*\n(.*?)(?=\n\nRISKS:|\nRISKS:)", text, re.DOTALL)

    impl_val = impl_match.group(1).strip() if impl_match else ""
    tests_val = tests_match.group(1).strip() if tests_match else ""
    sec_val = sec_match.group(1).strip() if sec_match else ""

    risks = re.findall(r"RISKS:\s*\n((?:- .*\n?)*)", text)
    risks_list = [line.strip("- ").strip() for line in risks[0].splitlines() if line.strip() and "(none)" not in line] if risks else []

    blockers = re.findall(r"BLOCKERS:\s*\n((?:- .*\n?)*)", text)
    blockers_list = [line.strip("- ").strip() for line in blockers[0].splitlines() if line.strip() and "(none)" not in line] if blockers else []

    return AgentReport(
        role=matching_role,
        task=task_val,
        understood_requirement=req_val,
        files_inspected=inspected_files,
        files_changed=changed_files,
        implementation=impl_val,
        tests=tests_val,
        security_considerations=sec_val,
        risks=risks_list,
        blockers=blockers_list,
        final_status=status_val,
    )


class ValidationResult(BaseModel):
    is_valid: bool
    violations: list[str] = Field(default_factory=list)


def validate_agent_report(report: AgentReport) -> ValidationResult:
    """Validate that the agent report satisfies ownership, formatting, and security invariants."""
    violations: list[str] = []
    role_def = ROLE_REGISTRY.get(report.role)

    # 1. Check required sections
    if not report.understood_requirement:
        violations.append("Missing required section: UNDERSTOOD REQUIREMENT")
    if not report.implementation:
        violations.append("Missing required section: IMPLEMENTATION")
    if not report.tests:
        violations.append("Missing required section: TESTS")
    if not report.security_considerations:
        violations.append("Missing required section: SECURITY CONSIDERATIONS")

    # 2. Check file ownership boundaries
    if role_def and role_def.allowed_file_patterns != ["*"]:
        for file in report.files_changed:
            normalized = file.replace("\\", "/")
            matched = False
            for pattern in role_def.allowed_file_patterns:
                pat = pattern.replace("*", ".*")
                if re.match(pat, normalized):
                    matched = True
                    break
            if not matched:
                violations.append(
                    f"File ownership violation: {report.role.value} cannot modify '{file}'. "
                    f"Allowed patterns: {role_def.allowed_file_patterns}"
                )

    # 3. Security anti-bypass inspection
    combined_content = f"{report.implementation} {report.security_considerations} {report.tests}".lower()

    forbidden_patterns = [
        (r"disable(?:d)?\s+(?:auth|authentication|jwt|signature)", "Attempt to disable authentication"),
        (r"dev_auth_bypass\s*=\s*(?:true|1)", "Attempt to enable DEV_AUTH_BYPASS in implementation"),
        (r"skip(?:ped)?\s+approval", "Attempt to bypass human approval gate"),
        (r"weaken(?:ed)?\s+test", "Attempt to weaken test assertions"),
        (r"delete(?:d)?\s+failing\s+test", "Attempt to delete failing tests instead of fixing code"),
        (r"hardcode(?:d)?\s+(?:secret|password|api[_-]?key|token)", "Attempt to hardcode secret credentials"),
        (r"redesign(?:ed)?\s+ui", "Attempt to redesign user interface (prohibited by UI/UX protection rule)"),
        (r"new\s+(?:color\s+palette|theme\s+overhaul|layout\s+overhaul)", "Prohibited visual styling overhaul"),
    ]

    for pat, desc in forbidden_patterns:
        if re.search(pat, combined_content):
            violations.append(f"Security invariant violation: {desc}")

    return ValidationResult(is_valid=(len(violations) == 0), violations=violations)
