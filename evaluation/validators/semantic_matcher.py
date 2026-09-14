"""Semantic finding matcher and location/severity/category evaluator."""

import os
import re
from dataclasses import dataclass, field
from typing import Any

from app.agents.schemas.finding import FindingCategory, FindingSeverity, ReviewFinding
from evaluation.scenarios.schema import (
    BenchmarkScenario,
    FindingClassification,
    GroundTruthFinding,
)

SEVERITY_ORDER = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

CATEGORY_COMPATIBILITY = {
    "SECURITY": {"SECURITY"},
    "BUG": {"BUG", "ERROR_HANDLING", "EDGE_CASES"},
    "ERROR_HANDLING": {"ERROR_HANDLING", "BUG", "EDGE_CASES"},
    "EDGE_CASES": {"EDGE_CASES", "BUG", "ERROR_HANDLING"},
    "TEST": {"TEST", "CONTRACT", "TEST_COVERAGE"},
    "CONTRACT": {"CONTRACT", "TEST", "TEST_COVERAGE"},
    "TEST_COVERAGE": {"TEST_COVERAGE", "TEST", "CONTRACT"},
    "PERFORMANCE": {"PERFORMANCE"},
    "GENERAL_CORRECTNESS": {"GENERAL_CORRECTNESS", "BUG", "ERROR_HANDLING"},
}


def normalize_path(path: str) -> str:
    """Normalize file path for cross-platform and relative comparison."""
    p = path.replace("\\", "/").strip()
    if p.startswith("./"):
        p = p[2:]
    return p


def tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase alphanumeric keywords."""
    return set(re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower()))


@dataclass
class FindingEvaluationDetail:
    """Detailed evaluation metrics for an individual predicted finding."""

    finding_id: str
    predicted_title: str
    predicted_category: str
    predicted_severity: str
    predicted_file: str
    predicted_line: int
    matched_ground_truth_id: str | None
    classification: FindingClassification
    category_match: bool
    category_score: float
    severity_match: bool
    severity_score: float
    severity_direction: str  # "EXACT", "OVER", "UNDER", "N/A"
    location_match: bool
    location_score: float
    valid_line_in_diff: bool
    wrong_file: bool
    wrong_line: bool
    semantic_similarity: float
    factuality_score: float
    actionability_score: float
    remediation_useful: bool
    notes: str = ""


@dataclass
class MatchResult:
    """Aggregated evaluation results for a scenario execution."""

    scenario_id: str
    true_positives: list[FindingEvaluationDetail] = field(default_factory=list)
    false_positives: list[FindingEvaluationDetail] = field(default_factory=list)
    false_negatives: list[GroundTruthFinding] = field(default_factory=list)

    # Line accuracy metrics
    total_predicted: int = 0
    valid_line_count: int = 0
    invalid_line_count: int = 0
    wrong_file_count: int = 0
    wrong_line_count: int = 0

    # Severity accuracy metrics
    exact_severity_count: int = 0
    over_severity_count: int = 0
    under_severity_count: int = 0

    # Category accuracy
    category_matches: int = 0

    # Redundancy / Duplicate
    raw_candidates_count: int = 0
    final_findings_count: int = 0
    duplicate_count: int = 0


class SemanticFindingMatcher:
    """
    Evaluates system-predicted findings against benchmark ground-truth findings.
    Does NOT require exact string equality; evaluates semantic correctness,
    root-cause concept overlap, category compatibility, and location proximity.
    """

    def __init__(
        self,
        line_tolerance: int = 4,
        min_semantic_similarity: float = 0.25,
    ):
        self.line_tolerance = line_tolerance
        self.min_semantic_similarity = min_semantic_similarity

    def evaluate_scenario(
        self,
        scenario: BenchmarkScenario,
        predicted_findings: list[ReviewFinding],
        valid_lines_by_file: dict[str, dict[str, list[int]]] | None = None,
        raw_candidates_count: int | None = None,
        duplicate_count: int = 0,
    ) -> MatchResult:
        """
        Match and score predicted findings against the scenario's ground truth.
        """
        result = MatchResult(
            scenario_id=scenario.scenario_id,
            raw_candidates_count=raw_candidates_count if raw_candidates_count is not None else len(predicted_findings),
            final_findings_count=len(predicted_findings),
            duplicate_count=duplicate_count,
        )

        unmatched_gt = {gt.finding_id: gt for gt in scenario.ground_truth_findings}
        matched_gt_ids: set[str] = set()

        for pred in predicted_findings:
            result.total_predicted += 1
            pred_file = normalize_path(pred.file_path)
            pred_line = pred.line_number
            pred_cat = pred.category.value if hasattr(pred.category, "value") else str(pred.category)
            pred_sev = pred.severity.value if hasattr(pred.severity, "value") else str(pred.severity)

            # 1. Line Boundary & Membership Evaluation
            is_valid_line = True
            is_wrong_file = True
            is_wrong_line = False

            if valid_lines_by_file:
                # Check file existence in diff
                norm_diff_files = {normalize_path(k): k for k in valid_lines_by_file.keys()}
                if pred_file in norm_diff_files:
                    is_wrong_file = False
                    orig_key = norm_diff_files[pred_file]
                    valid_lines = valid_lines_by_file[orig_key].get(pred.side, [])
                    if valid_lines and pred_line not in valid_lines:
                        is_valid_line = False
                        is_wrong_line = True
                else:
                    is_valid_line = False
                    is_wrong_file = True
            else:
                is_wrong_file = False

            if is_valid_line:
                result.valid_line_count += 1
            else:
                result.invalid_line_count += 1
                if is_wrong_file:
                    result.wrong_file_count += 1
                elif is_wrong_line:
                    result.wrong_line_count += 1

            # 2. Match against candidate Ground Truth findings
            best_gt: GroundTruthFinding | None = None
            best_score = -1.0
            best_semantic_sim = 0.0

            pred_tokens = tokenize(f"{pred.title} {pred.description} {pred.impact} {pred.recommendation}")

            for gt in scenario.ground_truth_findings:
                gt_file = normalize_path(gt.file_path)
                # Must match target file
                if pred_file != gt_file and not (pred_file.endswith(gt_file) or gt_file.endswith(pred_file)):
                    continue

                # Proximity check
                line_dist = min(
                    abs(pred_line - gt.line_start),
                    abs(pred_line - gt.line_end),
                    0 if gt.line_start <= pred_line <= gt.line_end else 999,
                )
                if line_dist > self.line_tolerance:
                    continue

                # Semantic concept overlap
                gt_tokens = tokenize(f"{gt.root_cause} {' '.join(gt.keywords)}")
                intersection = pred_tokens.intersection(gt_tokens)
                union = pred_tokens.union(gt_tokens)
                sim = len(intersection) / len(union) if union else 0.0

                # Keyword hit bonus
                keyword_hits = sum(1 for kw in gt.keywords if kw.lower() in f"{pred.title} {pred.description}".lower())
                composite_score = sim + (0.2 * keyword_hits) - (0.05 * line_dist)

                if composite_score > best_score:
                    best_score = composite_score
                    best_gt = gt
                    best_semantic_sim = sim

            # 3. Determine match classification & scores
            if best_gt and (best_semantic_sim >= self.min_semantic_similarity or best_score > 0.3):
                # We matched a ground truth entry!
                cat_match = self._is_category_compatible(pred_cat, best_gt.category)
                cat_score = 1.0 if pred_cat.upper() == best_gt.category.upper() else (0.75 if cat_match else 0.0)
                if cat_match:
                    result.category_matches += 1

                sev_match, sev_score, sev_dir = self._evaluate_severity(pred_sev, best_gt.severity)
                if sev_match:
                    result.exact_severity_count += 1
                elif sev_dir == "OVER":
                    result.over_severity_count += 1
                elif sev_dir == "UNDER":
                    result.under_severity_count += 1

                loc_match = (best_gt.line_start - self.line_tolerance) <= pred_line <= (best_gt.line_end + self.line_tolerance)
                loc_score = 1.0 if (best_gt.line_start <= pred_line <= best_gt.line_end) else 0.75

                # Quality checks
                factuality_score = 0.95 if is_valid_line and len(pred.evidence) > 0 else 0.6
                actionability_score = self._evaluate_actionability(pred.recommendation)
                remediation_useful = actionability_score >= 0.7

                if best_gt.is_false_positive_trap:
                    # System generated a finding on intentional/safe code (False Positive!)
                    detail = FindingEvaluationDetail(
                        finding_id=pred.finding_id,
                        predicted_title=pred.title,
                        predicted_category=pred_cat,
                        predicted_severity=pred_sev,
                        predicted_file=pred_file,
                        predicted_line=pred_line,
                        matched_ground_truth_id=best_gt.finding_id,
                        classification=FindingClassification.FALSE_POSITIVE,
                        category_match=cat_match,
                        category_score=cat_score,
                        severity_match=sev_match,
                        severity_score=sev_score,
                        severity_direction=sev_dir,
                        location_match=loc_match,
                        location_score=loc_score,
                        valid_line_in_diff=is_valid_line,
                        wrong_file=is_wrong_file,
                        wrong_line=is_wrong_line,
                        semantic_similarity=best_semantic_sim,
                        factuality_score=factuality_score,
                        actionability_score=actionability_score,
                        remediation_useful=remediation_useful,
                        notes="Fell into False Positive trap: Flagged code that has caller or intentional guard.",
                    )
                    result.false_positives.append(detail)
                else:
                    # Real defect matched: True Positive!
                    matched_gt_ids.add(best_gt.finding_id)
                    unmatched_gt.pop(best_gt.finding_id, None)

                    detail = FindingEvaluationDetail(
                        finding_id=pred.finding_id,
                        predicted_title=pred.title,
                        predicted_category=pred_cat,
                        predicted_severity=pred_sev,
                        predicted_file=pred_file,
                        predicted_line=pred_line,
                        matched_ground_truth_id=best_gt.finding_id,
                        classification=FindingClassification.TRUE_POSITIVE,
                        category_match=cat_match,
                        category_score=cat_score,
                        severity_match=sev_match,
                        severity_score=sev_score,
                        severity_direction=sev_dir,
                        location_match=loc_match,
                        location_score=loc_score,
                        valid_line_in_diff=is_valid_line,
                        wrong_file=is_wrong_file,
                        wrong_line=is_wrong_line,
                        semantic_similarity=best_semantic_sim,
                        factuality_score=factuality_score,
                        actionability_score=actionability_score,
                        remediation_useful=remediation_useful,
                        notes="Successfully detected and grounded real defect.",
                    )
                    result.true_positives.append(detail)
            else:
                # No GT matched -> Spurious finding (False Positive)
                act_score = self._evaluate_actionability(pred.recommendation)
                detail = FindingEvaluationDetail(
                    finding_id=pred.finding_id,
                    predicted_title=pred.title,
                    predicted_category=pred_cat,
                    predicted_severity=pred_sev,
                    predicted_file=pred_file,
                    predicted_line=pred_line,
                    matched_ground_truth_id=None,
                    classification=FindingClassification.FALSE_POSITIVE,
                    category_match=False,
                    category_score=0.0,
                    severity_match=False,
                    severity_score=0.0,
                    severity_direction="N/A",
                    location_match=False,
                    location_score=0.0,
                    valid_line_in_diff=is_valid_line,
                    wrong_file=is_wrong_file,
                    wrong_line=is_wrong_line,
                    semantic_similarity=best_semantic_sim,
                    factuality_score=0.5 if is_valid_line else 0.0,
                    actionability_score=act_score,
                    remediation_useful=act_score >= 0.7,
                    notes="Unmatched candidate finding: Spurious false positive.",
                )
                result.false_positives.append(detail)

        # 4. Remaining unmatched GT entries (excluding intentional false positive traps) are False Negatives!
        for gt in unmatched_gt.values():
            if not gt.is_false_positive_trap:
                result.false_negatives.append(gt)

        return result

    def _is_category_compatible(self, pred_cat: str, gt_cat: str) -> bool:
        pred_u = pred_cat.upper()
        gt_u = gt_cat.upper()
        if pred_u == gt_u:
            return True
        allowed = CATEGORY_COMPATIBILITY.get(gt_u, {gt_u})
        return pred_u in allowed

    def _evaluate_severity(self, pred_sev: str, gt_sev: str) -> tuple[bool, float, str]:
        p_val = SEVERITY_ORDER.get(pred_sev.upper(), 2)
        g_val = SEVERITY_ORDER.get(gt_sev.upper(), 2)

        if p_val == g_val:
            return True, 1.0, "EXACT"

        diff = abs(p_val - g_val)
        direction = "OVER" if p_val > g_val else "UNDER"

        if diff == 1:
            score = 0.75
        elif diff == 2:
            score = 0.25
        else:
            score = 0.0

        return False, score, direction

    def _evaluate_actionability(self, recommendation: str | None) -> float:
        """Deterministic evaluation of remediation actionability."""
        if not recommendation or len(recommendation.strip()) < 15:
            return 0.2

        vague_phrases = [
            "consider adding",
            "you might want to",
            "ensure proper",
            "make sure to",
            "look into",
            "please verify",
        ]
        text_lower = recommendation.lower()
        if any(vp in text_lower for vp in vague_phrases) and len(recommendation) < 40:
            return 0.4

        has_code_mention = "`" in recommendation or any(
            kw in text_lower for kw in ["raise", "return", "import", "def ", "class ", "if ", "try:"]
        )
        return 0.95 if has_code_mention else 0.75
