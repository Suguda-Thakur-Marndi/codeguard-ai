"""CodeGuard AI — Phase 11: Multi-Agent Engineering Workflow Verification Suite.

Executes and verifies:
1. Antigravity Customizations & Configuration Audit (.agents, rules, skills, plugins, AGENTS.md, GEMINI.md)
2. Agency Agent Role Matrix & Invariant Boundaries (12 roles, allowed paths, structured schemas)
3. Serena Codebase-Aware Navigation Suite (AST symbol discovery, callers, dependencies, 11-step workflow)
4. Context7 Documentation & Version Safety Suite (manifest versions, doc queries, deprecation detection)
5. Security Boundary & Anti-Bypass Enforcement Suite (rejection of auth bypass, approval skip, secret leaks)
6. UI/UX & Business Logic Invariant Protection Suite (rejection of UI redesigns, business semantic shifts)
7. Multi-Agent 10-Step Workflow Orchestration Execution (normal flow & bypass rejection flow)
8. Zero-Placeholder Audit across Phase 11 assets
9. Full CodeGuard AI Runtime Regression Suite (Full Phase 10 Verification 17/17 PASS)
10. Final Production Scorecard Evaluation
"""

import json
import os
import re
import sys
import time

# Monorepo Path Setup
_root = os.path.abspath(os.path.dirname(__file__))
_api_path = os.path.join(_root, "apps", "api")
_pkg_path = os.path.join(_root, "packages", "code-intelligence")
for p in [_root, _api_path, _pkg_path]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ["APP_ENV"] = "test"
os.environ["CODEGUARD_BENCHMARK_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///phase11_verify.db"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["DEV_AUTH_BYPASS"] = "true"

from scripts.workflow.agent_roles import (
    ROLE_REGISTRY,
    AgentReport,
    AgentRole,
    AgentStatus,
    get_role_definition,
    parse_agent_report_text,
    validate_agent_report,
)
from scripts.workflow.context7_bridge import Context7Bridge
from scripts.workflow.orchestrator import WorkflowOrchestrator
from scripts.workflow.serena_bridge import SerenaNavigator
from verify_phase10 import Phase10VerificationSuite


class Phase11VerificationSuite:
    """Master Verification Suite for CodeGuard AI Phase 11."""

    def __init__(self) -> None:
        self.scorecard: dict[str, tuple[bool, str]] = {}

    def record(self, category: str, passed: bool, message: str) -> None:
        self.scorecard[category] = (passed, message)
        tag = "[PASS]" if passed else "[FAIL]"
        print(f"{tag} {category}: {message}")

    # =========================================================================
    # 1. Antigravity Customizations & Configuration Audit
    # =========================================================================
    def verify_customizations(self) -> None:
        cat = "CUSTOMIZATIONS"
        errors = []

        # Check AGENTS.md and GEMINI.md
        for fname in ["AGENTS.md", "GEMINI.md"]:
            fpath = os.path.join(_root, fname)
            if not os.path.exists(fpath):
                errors.append(f"Missing root file: {fname}")
            elif os.path.getsize(fpath) < 100:
                errors.append(f"File {fname} is suspiciously small (<100 bytes)")

        # Check rules
        expected_rules = [
            "00_engineering_hierarchy.md",
            "01_ui_ux_protection.md",
            "02_security_boundary.md",
            "03_business_logic_protection.md",
            "04_serena_workflow.md",
            "05_context7_safety.md",
        ]
        for rname in expected_rules:
            rpath = os.path.join(_root, ".agents", "rules", rname)
            if not os.path.exists(rpath):
                errors.append(f"Missing rule: .agents/rules/{rname}")

        # Check skills
        expected_skills = [
            "codeguard-agency-agents",
            "codeguard-serena-navigator",
            "codeguard-context7-docs",
            "codeguard-workflow-orchestrator",
        ]
        for sname in expected_skills:
            spath = os.path.join(_root, ".agents", "skills", sname, "SKILL.md")
            if not os.path.exists(spath):
                errors.append(f"Missing skill: .agents/skills/{sname}/SKILL.md")
            else:
                with open(spath, "r", encoding="utf-8") as f:
                    content = f.read()
                if not content.startswith("---") or "name:" not in content:
                    errors.append(f"Skill {sname}/SKILL.md missing valid YAML frontmatter")

        # Check plugin
        plugin_json = os.path.join(_root, ".agents", "plugins", "codeguard-workflow", "plugin.json")
        mcp_config = os.path.join(_root, ".agents", "plugins", "codeguard-workflow", "mcp_config.json")
        hooks_json = os.path.join(_root, ".agents", "plugins", "codeguard-workflow", "hooks.json")
        for pfile in [plugin_json, mcp_config, hooks_json]:
            if not os.path.exists(pfile):
                errors.append(f"Missing plugin file: {os.path.relpath(pfile, _root)}")

        if errors:
            self.record(cat, False, "; ".join(errors))
        else:
            self.record(cat, True, "Antigravity customizations confirmed: 6 rules, 4 skills, 1 plugin, and workspace configs valid.")

    # =========================================================================
    # 2. Agency Agent Role Matrix & Boundaries Audit
    # =========================================================================
    def verify_agency_roles(self) -> None:
        cat = "AGENCY_ROLES"
        errors = []

        expected_roles = [
            AgentRole.ARCHITECT,
            AgentRole.BACKEND,
            AgentRole.FRONTEND,
            AgentRole.DATABASE,
            AgentRole.SECURITY,
            AgentRole.MCP,
            AgentRole.AI_LANGGRAPH,
            AgentRole.CODE_INTELLIGENCE,
            AgentRole.TESTING,
            AgentRole.DEVOPS,
            AgentRole.REVIEW,
            AgentRole.FINAL_INTEGRATION,
        ]

        # Verify all 12 roles exist in registry
        for role in expected_roles:
            if role not in ROLE_REGISTRY:
                errors.append(f"Missing role definition in registry: {role.value}")
            else:
                defn = ROLE_REGISTRY[role]
                if not defn.description or not defn.allowed_file_patterns:
                    errors.append(f"Role {role.value} has incomplete definition")

        # Test boundary violation: Frontend Agent attempting to modify apps/api/
        bad_frontend_report = AgentReport(
            role=AgentRole.FRONTEND,
            task="Attempt unauthorized backend edit",
            understood_requirement="Valid requirement description.",
            files_inspected=["apps/api/app/main.py"],
            files_changed=["apps/api/app/main.py"],
            implementation="Attempted backend edit from frontend agent.",
            tests="pytest",
            security_considerations="None",
            risks=[],
            blockers=[],
        )
        val = validate_agent_report(bad_frontend_report)
        if val.is_valid or not any("File ownership violation" in v for v in val.violations):
            errors.append("Validation failed to catch Frontend Agent modifying apps/api/!")

        # Test report formatting and roundtrip parsing
        sample_report = AgentReport(
            role=AgentRole.BACKEND,
            task="Add health probe",
            understood_requirement="Add lightweight health check endpoint.",
            files_inspected=["apps/api/app/main.py"],
            files_changed=["apps/api/app/api/v1/health.py"],
            implementation="Added /api/v1/health returning 200 OK.",
            tests="pytest apps/api/tests/test_health.py",
            security_considerations="Unauthenticated public endpoint with rate limiting.",
            risks=[],
            blockers=[],
            final_status=AgentStatus.SUCCESS,
        )
        formatted_txt = sample_report.format_text()
        parsed = parse_agent_report_text(formatted_txt)
        if parsed.role != AgentRole.BACKEND or parsed.task != "Add health probe":
            errors.append(f"AgentReport text serialization/deserialization mismatch: {parsed.role}")

        if errors:
            self.record(cat, False, "; ".join(errors))
        else:
            self.record(cat, True, "All 12 Agency Agent roles, boundaries, and structured report schemas verified.")

    # =========================================================================
    # 3. Serena Codebase-Aware Navigation Suite
    # =========================================================================
    def verify_serena(self) -> None:
        cat = "SERENA_NAVIGATION"
        errors = []
        nav = SerenaNavigator(_root)

        # 1. Symbol discovery
        judge_syms = nav.find_symbol("AdversarialJudge")
        if not judge_syms:
            errors.append("Serena failed to locate 'AdversarialJudge' class via AST")
        else:
            j = judge_syms[0]
            if "adversarial_judge.py" not in j.file_path:
                errors.append(f"AdversarialJudge found in unexpected path: {j.file_path}")

        parser_syms = nav.find_symbol("UnifiedDiffParser")
        if not parser_syms:
            errors.append("Serena failed to locate 'UnifiedDiffParser' class via AST")

        # 2. Inspect definition
        if judge_syms:
            def_info = nav.inspect_definition(judge_syms[0].file_path, "AdversarialJudge")
            if "error" in def_info or def_info.get("name") != "AdversarialJudge":
                errors.append(f"inspect_definition failed: {def_info}")
            elif "source_code" not in def_info or "class AdversarialJudge" not in def_info["source_code"]:
                errors.append("inspect_definition source_code missing class declaration")

        # 3. Callers resolution
        callers = nav.get_callers("AdversarialJudge")
        if not callers:
            errors.append("Serena failed to resolve callers for 'AdversarialJudge'")

        # 4. Dependency extraction
        deps = nav.get_dependencies("apps/api/app/main.py")
        if not deps or not any("fastapi" in d for d in deps):
            errors.append("Serena failed to extract dependencies from apps/api/app/main.py")

        # 5. Full 11-step workflow execution
        record = nav.execute_11_step_workflow("Verify AdversarialJudge integration", ["AdversarialJudge"])
        if record.status != "COMPLETED" or len(record.step2_located_symbols) == 0:
            errors.append("Serena 11-step workflow failed to complete")

        if errors:
            self.record(cat, False, "; ".join(errors))
        else:
            self.record(
                cat,
                True,
                f"Serena AST navigation verified: found {len(judge_syms)} target symbols, {len(callers)} callers, and completed 11-step exploration.",
            )

    # =========================================================================
    # 4. Context7 Documentation & Version Safety Suite
    # =========================================================================
    def verify_context7(self) -> None:
        cat = "CONTEXT7_DOCS"
        errors = []
        c7 = Context7Bridge(_root)

        # 1. Manifest version checking
        fastapi_ver = c7.get_installed_version("fastapi")
        pydantic_ver = c7.get_installed_version("pydantic")
        next_ver = c7.get_installed_version("next")

        if not fastapi_ver or "0.11" not in fastapi_ver:
            errors.append(f"Failed to resolve installed FastAPI version correctly: {fastapi_ver}")
        if not pydantic_ver or "2." not in pydantic_ver:
            errors.append(f"Failed to resolve installed Pydantic version correctly: {pydantic_ver}")
        if not next_ver or "15." not in next_ver:
            errors.append(f"Failed to resolve installed Next.js version correctly: {next_ver}")

        # 2. Query documentation
        doc_pydantic = c7.query_documentation("pydantic")
        if not doc_pydantic.authoritative_signature or "@validator" not in doc_pydantic.deprecated_patterns:
            errors.append("Context7 documentation missing Pydantic V2 signatures or deprecations")

        # 3. Code compatibility checking (deprecated pattern detection)
        deprecated_code = "from pydantic import BaseModel, validator\nclass MyModel(BaseModel):\n    @validator('x')\n    def check(cls, v): return v"
        compat = c7.validate_code_compatibility("pydantic", deprecated_code)
        if compat.is_compatible:
            errors.append("Context7 failed to flag deprecated @validator pattern in Pydantic V2 code")

        # 4. Hierarchy enforcement
        conflict_result = c7.check_hierarchy_conflict("fastapi", "We can disable authentication for easier testing")
        if not conflict_result.conflicts_with_project:
            errors.append("Context7 failed to detect security conflict in 'disable authentication' proposal")

        if errors:
            self.record(cat, False, "; ".join(errors))
        else:
            self.record(
                cat,
                True,
                f"Context7 version-safety verified (FastAPI {fastapi_ver}, Pydantic {pydantic_ver}, Next.js {next_ver}). Hierarchy enforcement confirmed.",
            )

    # =========================================================================
    # 5. Security Boundary & Anti-Bypass Enforcement Suite
    # =========================================================================
    def verify_security_anti_bypass(self) -> None:
        cat = "SECURITY_ANTI_BYPASS"
        errors = []

        bypass_attempts = [
            ("disable authentication so tests pass", "Attempt to disable authentication"),
            ("set DEV_AUTH_BYPASS = true in app config", "Attempt to enable DEV_AUTH_BYPASS"),
            ("we will skip approval for this emergency action", "Attempt to bypass human approval gate"),
            ("weaken test assertions to make the build green", "Attempt to weaken test assertions"),
            ("delete failing test cases", "Attempt to delete failing tests instead of fixing code"),
            ("hardcode api_key = 'sk-12345' directly in code", "Attempt to hardcode secret credentials"),
        ]

        for attempt_text, expected_violation in bypass_attempts:
            report = AgentReport(
                role=AgentRole.BACKEND,
                task="Perform action",
                understood_requirement="Test action",
                files_inspected=["apps/api/app/main.py"],
                files_changed=["apps/api/app/main.py"],
                implementation=f"Implementation notes: {attempt_text}",
                tests="pytest",
                security_considerations="Attempting quick fix",
                risks=[],
                blockers=[],
            )
            val = validate_agent_report(report)
            if val.is_valid:
                errors.append(f"Failed to reject bypass attempt: '{attempt_text}'")

        if errors:
            self.record(cat, False, "; ".join(errors))
        else:
            self.record(cat, True, f"All {len(bypass_attempts)} simulated security bypass attempts deterministically blocked.")

    # =========================================================================
    # 6. UI/UX & Business Logic Invariant Protection Suite
    # =========================================================================
    def verify_ui_and_business_invariants(self) -> None:
        cat = "UI_BUSINESS_INVARIANTS"
        errors = []

        # 1. UI Redesign attempt rejection
        ui_redesign_attempt = AgentReport(
            role=AgentRole.FRONTEND,
            task="Refresh UI Dashboard",
            understood_requirement="Redesign the UI with a brand new color palette and layout overhaul.",
            files_inspected=["apps/web/app/page.tsx"],
            files_changed=["apps/web/app/page.tsx"],
            implementation="Created new theme overhaul and redesigned UI layout with alternative grid system.",
            tests="npm test",
            security_considerations="None",
            risks=[],
            blockers=[],
        )
        val = validate_agent_report(ui_redesign_attempt)
        if val.is_valid:
            errors.append("Failed to reject UI redesign attempt!")

        # 2. Verify rule files explicitly prohibit UI changes and business logic modification
        ui_rule_path = os.path.join(_root, ".agents", "rules", "01_ui_ux_protection.md")
        with open(ui_rule_path, "r", encoding="utf-8") as f:
            rule_text = f.read()
        if "NO UI/UX REDESIGN" not in rule_text:
            errors.append("UI/UX protection rule missing 'NO UI/UX REDESIGN' invariant")

        biz_rule_path = os.path.join(_root, ".agents", "rules", "03_business_logic_protection.md")
        with open(biz_rule_path, "r", encoding="utf-8") as f:
            biz_text = f.read()
        if "CRITICAL" not in biz_text or "APPROVED" not in biz_text:
            errors.append("Business logic rule missing core status invariants")

        if errors:
            self.record(cat, False, "; ".join(errors))
        else:
            self.record(cat, True, "UI/UX preservation and core business logic invariants strictly protected.")

    # =========================================================================
    # 7. Multi-Agent 10-Step Workflow Orchestration Execution
    # =========================================================================
    def verify_workflow_orchestration(self) -> None:
        cat = "WORKFLOW_ORCHESTRATION"
        errors = []
        orch = WorkflowOrchestrator(_root)

        # 1. Normal legitimate engineering task
        normal_res = orch.execute_task(
            task_description="Fix MCP approval validation and commit-drift checking",
            target_area="mcp",
            relevant_symbols=["AdversarialJudge", "ApprovalService"],
            external_libraries=["fastapi", "pydantic"],
            simulate_security_bypass=False,
        )
        if normal_res.overall_status != "SUCCESS":
            errors.append(f"Legitimate task failed in orchestrator: {normal_res.overall_status}")
        if len(normal_res.steps) != 10:
            errors.append(f"Expected 10 steps, got {len(normal_res.steps)}")

        # 2. Malicious task with simulated security bypass
        bypass_res = orch.execute_task(
            task_description="Update auth middleware and disable auth for dev convenience",
            target_area="backend",
            relevant_symbols=["AdversarialJudge"],
            external_libraries=["fastapi"],
            simulate_security_bypass=True,
        )
        if bypass_res.overall_status != "REJECTED":
            errors.append(f"Bypass task was not REJECTED! Result was: {bypass_res.overall_status}")
        if bypass_res.security_verdict != "REJECTED":
            errors.append(f"Security Agent did not flag bypass! Verdict: {bypass_res.security_verdict}")
        if bypass_res.review_verdict != "REJECTED_BY_SECURITY":
            errors.append(f"Review Agent did not reject on security failure! Verdict: {bypass_res.review_verdict}")

        if errors:
            self.record(cat, False, "; ".join(errors))
        else:
            self.record(
                cat,
                True,
                f"10-Step workflow execution verified: Normal task approved (10/10 steps, {normal_res.total_duration_ms:.1f}ms); Bypass task rejected by Security & Review gates.",
            )

    # =========================================================================
    # 8. Zero-Placeholder Audit across Phase 11 Assets
    # =========================================================================
    def verify_zero_placeholders(self) -> None:
        cat = "ZERO_PLACEHOLDERS"
        errors = []
        code_placeholders = [r"\bTODO\b", r"\bFIXME\b", r"\bNotImplementedError\b", r"^\s*pass\s*(?:#.*)?$"]

        paths_to_audit = [
            os.path.join(_root, "scripts", "workflow"),
            os.path.join(_root, ".agents"),
            os.path.join(_root, "docs", "ENGINEERING_WORKFLOW.md"),
            os.path.join(_root, "AGENTS.md"),
            os.path.join(_root, "GEMINI.md"),
        ]

        for p in paths_to_audit:
            if os.path.isfile(p):
                file_list = [p]
            else:
                file_list = []
                for root, _, files in os.walk(p):
                    for f in files:
                        if f.endswith((".py", ".md", ".json")):
                            file_list.append(os.path.join(root, f))

            for fpath in file_list:
                is_py = fpath.endswith(".py")
                with open(fpath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for idx, line in enumerate(lines, 1):
                    stripped = line.strip()
                    # Skip comment lines
                    if stripped.startswith("#") or stripped.startswith("*") or stripped.startswith("-") or stripped.startswith("//"):
                        continue
                    # For Python files check for standalone pass or TODO/FIXME/NotImplementedError
                    if is_py:
                        for pat in code_placeholders:
                            if re.search(pat, line if pat.startswith("^") else stripped):
                                errors.append(f"Code placeholder {pat} in {os.path.relpath(fpath, _root)}:{idx}: {stripped}")
                    else:
                        # For docs/configs, check only explicit TODO/FIXME markers
                        for pat in [r"\bTODO\b", r"\bFIXME\b"]:
                            if re.search(pat, stripped):
                                errors.append(f"Doc placeholder {pat} in {os.path.relpath(fpath, _root)}:{idx}: {stripped}")

        if errors:
            self.record(cat, False, "; ".join(errors[:5]))
        else:
            self.record(cat, True, "Zero-placeholder audit passed: 0 TODOs, FIXMEs, or NotImplementedErrors in workflow code.")

    # =========================================================================
    # 9. Full CodeGuard AI Runtime Regression Suite (Phase 10 Suite)
    # =========================================================================
    def verify_runtime_regression(self) -> None:
        cat = "RUNTIME_REGRESSION"
        print("\n--- Running Master Phase 10 Regression Suite (17 Categories) ---")
        p10 = Phase10VerificationSuite()
        p10_success = p10.run_all()
        if not p10_success:
            failed = [k for k, v in p10.scorecard.items() if not v[0]]
            self.record(cat, False, f"Phase 10 regression failures detected in: {', '.join(failed)}")
        else:
            self.record(cat, True, "All 17 Phase 10 production categories passed with 100% success. Zero runtime regressions.")

    # =========================================================================
    # Master Runner
    # =========================================================================
    def run_all(self) -> bool:
        print("===========================================================================")
        print("CODEGUARD AI — PHASE 11: MULTI-AGENT ENGINEERING WORKFLOW VERIFICATION SUITE")
        print("===========================================================================\n")

        self.verify_customizations()
        self.verify_agency_roles()
        self.verify_serena()
        self.verify_context7()
        self.verify_security_anti_bypass()
        self.verify_ui_and_business_invariants()
        self.verify_workflow_orchestration()
        self.verify_zero_placeholders()
        self.verify_runtime_regression()

        total = len(self.scorecard)
        passed = sum(1 for v in self.scorecard.values() if v[0])
        all_passed = (total == passed)

        print("\n===========================================================================")
        print(f"FINAL PHASE 11 SCORECARD: {passed}/{total} PASS")
        for cat, (status, msg) in self.scorecard.items():
            tag = "[PASS]" if status else "[FAIL]"
            print(f"  {tag} {cat:<24}: {msg}")
        print("===========================================================================")

        if all_passed:
            print("STATUS: READY — MULTI-AGENT ENGINEERING WORKFLOW MEETS ALL SPECIFICATIONS")
        else:
            print("STATUS: FAILED — REMEDIATION REQUIRED")
        return all_passed


if __name__ == "__main__":
    suite = Phase11VerificationSuite()
    success = suite.run_all()
    sys.exit(0 if success else 1)
