"""Deterministic Finding Validator enforcing diff boundaries, valid line numbers, and evidence grounding."""

from app.agents.schemas.finding import (
    EvidenceType,
    FindingStatus,
    ReviewFinding,
)
from app.core.logging import logger


class FindingValidator:
    """Strict deterministic post-generation validation of candidate findings against Code Intelligence rules."""

    @classmethod
    def validate_findings(
        cls,
        findings: list[ReviewFinding],
        changed_files: list[str],
        changed_lines_by_file: dict[str, dict[str, list[int]]],
        known_symbols: set[str] | None = None,
    ) -> tuple[list[ReviewFinding], list[ReviewFinding]]:
        """
        Validate all candidate findings.
        Returns: (validated_findings, invalid_findings)
        """
        validated: list[ReviewFinding] = []
        invalid: list[ReviewFinding] = []

        valid_files_set = set(changed_files)

        for finding in findings:
            rejection_reasons: list[str] = []

            # Rule 1: File must exist in changed files
            if finding.file_path not in valid_files_set:
                # Suffix fallback check (e.g. if model stripped src/ prefix)
                matched_file = next(
                    (f for f in valid_files_set if f.endswith(finding.file_path) or finding.file_path.endswith(f)),
                    None,
                )
                if matched_file:
                    finding.file_path = matched_file
                else:
                    rejection_reasons.append(
                        f"File '{finding.file_path}' does not exist among changed files {sorted(valid_files_set)}."
                    )

            # Rule 2: Line number must be positive integer
            if not isinstance(finding.line_number, int) or finding.line_number <= 0:
                rejection_reasons.append(f"Invalid line number: {finding.line_number}. Must be positive integer.")

            # Rule 3 & 4: Line must belong to allowed diff review lines
            side = (finding.side or "RIGHT").upper()
            allowed_lines = changed_lines_by_file.get(finding.file_path, {}).get(side, [])

            if finding.file_path in changed_lines_by_file:
                if finding.line_number not in allowed_lines:
                    # Check other side just in case
                    other_side = "LEFT" if side == "RIGHT" else "RIGHT"
                    other_allowed = changed_lines_by_file.get(finding.file_path, {}).get(other_side, [])
                    if finding.line_number in other_allowed:
                        # Auto-correct side
                        finding.side = other_side
                    else:
                        rejection_reasons.append(
                            f"Hallucinated line {finding.line_number}: line does not belong to valid {side} "
                            f"diff lines {sorted(allowed_lines)} for file '{finding.file_path}'."
                        )

            # Rule 5: Confidence must be within [0.0, 1.0]
            if not (0.0 <= finding.confidence <= 1.0):
                rejection_reasons.append(f"Invalid confidence score: {finding.confidence}. Must be between 0.0 and 1.0.")

            # Rule 6: Evidence must be non-empty
            if not finding.evidence:
                rejection_reasons.append("Missing evidence: finding contains no grounding evidence items.")
            else:
                for idx, ev in enumerate(finding.evidence):
                    if not ev.description or len(ev.description.strip()) < 5:
                        rejection_reasons.append(f"Evidence item #{idx + 1} has insufficient description.")
                    if ev.type not in EvidenceType.__members__.values():
                        rejection_reasons.append(f"Evidence item #{idx + 1} has invalid evidence type: {ev.type}.")

            # Rule 7: Required fields must be non-empty strings
            if not finding.title or len(finding.title.strip()) < 5:
                rejection_reasons.append("Finding title is missing or too short.")
            if not finding.description or len(finding.description.strip()) < 10:
                rejection_reasons.append("Finding description is missing or too short.")
            if not finding.impact or len(finding.impact.strip()) < 5:
                rejection_reasons.append("Finding impact is missing or too short.")
            if not finding.recommendation or len(finding.recommendation.strip()) < 5:
                rejection_reasons.append("Finding recommendation is missing or too short.")

            # Result routing
            if rejection_reasons:
                finding.status = FindingStatus.INVALID
                finding.validation_notes = "; ".join(rejection_reasons)
                invalid.append(finding)
                logger.warning(
                    f"Rejected candidate finding '{finding.title}' from {finding.agent_name}: {finding.validation_notes}",
                    extra={"file": finding.file_path, "line": finding.line_number},
                )
            else:
                finding.status = FindingStatus.VALID
                finding.validation_notes = "Verified: file exists, line belongs to valid diff region, evidence complete."
                validated.append(finding)

        return validated, invalid
