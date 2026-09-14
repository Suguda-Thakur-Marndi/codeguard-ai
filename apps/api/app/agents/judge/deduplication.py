"""Deterministic and semantic deduplication and root-cause grouping for code review findings."""

import uuid

from app.agents.schemas.finding import FindingSeverity, FindingStatus, ReviewFinding


class DeduplicationEngine:
    """
    Engine for identifying duplicate findings from multiple specialist agents,
    merging provenance into `source_agents`, and grouping related symptoms
    under shared `root_cause_id` without merging genuinely distinct defects.
    """

    @classmethod
    def deduplicate_and_group(
        cls, findings: list[ReviewFinding]
    ) -> tuple[list[ReviewFinding], list[ReviewFinding]]:
        """
        Deduplicate findings and group related symptoms.
        Returns:
            (canonical_findings, duplicate_findings)
        """
        if not findings:
            return [], []

        canonical: list[ReviewFinding] = []
        duplicates: list[ReviewFinding] = []

        for candidate in findings:
            matched_canonical = None
            for existing in canonical:
                if cls._is_duplicate(candidate, existing):
                    matched_canonical = existing
                    break

            if matched_canonical:
                # Merge candidate into existing canonical finding
                cls._merge_findings(matched_canonical, candidate)
                # Mark candidate as duplicate
                candidate.status = FindingStatus.REJECTED
                candidate.duplicate_of = matched_canonical.finding_id
                candidate.validation_notes = f"Merged as duplicate of finding {matched_canonical.finding_id}"
                duplicates.append(candidate)
            else:
                if not candidate.source_agents:
                    candidate.source_agents = [candidate.agent_name] if candidate.agent_name else []
                canonical.append(candidate)

        # Root-cause grouping across canonical findings
        cls._assign_root_causes(canonical)

        return canonical, duplicates

    @classmethod
    def _is_duplicate(cls, f1: ReviewFinding, f2: ReviewFinding) -> bool:
        """
        Determine whether two findings represent the same underlying defect.
        Checks:
        1. File path match
        2. Line proximity (within 3 lines)
        3. Symbol overlap or category correlation (e.g. Security + Bug on auth check)
        4. Semantic text correlation (title/description keywords)
        """
        if f1.file_path != f2.file_path:
            return False

        # Line proximity check
        line_diff = abs(f1.line_number - f2.line_number)
        if line_diff > 3:
            # Different locations in file
            return False

        # Same affected symbol check
        if f1.affected_symbol and f2.affected_symbol and f1.affected_symbol == f2.affected_symbol:
            return True

        # Check semantic title / description overlap
        t1 = f1.title.lower()
        t2 = f2.title.lower()
        words1 = set(t1.split())
        words2 = set(t2.split())
        common_words = words1.intersection(words2) - {"the", "a", "an", "in", "on", "of", "to", "for", "is", "at"}

        # High keyword overlap on same lines
        if len(common_words) >= 2:
            return True

        # Cross-agent correlation: Security missing auth + Bug unauthorized access
        auth_keywords = {"auth", "authorization", "permission", "unauthorized", "access"}
        if any(k in t1 for k in auth_keywords) and any(k in t2 for k in auth_keywords):
            return True

        return False

    @classmethod
    def _merge_findings(cls, target: ReviewFinding, source: ReviewFinding) -> None:
        """Merge provenance, evidence, and update severity/confidence if source is higher."""
        # Merge source agents
        agents = set(target.source_agents)
        if target.agent_name:
            agents.add(target.agent_name)
        if source.agent_name:
            agents.add(source.agent_name)
        agents.update(source.source_agents)
        target.source_agents = sorted(agents)

        # Severity priority hierarchy
        severity_order = {
            FindingSeverity.CRITICAL: 5,
            FindingSeverity.HIGH: 4,
            FindingSeverity.MEDIUM: 3,
            FindingSeverity.LOW: 2,
            FindingSeverity.ADVISORY: 1,
        }
        if severity_order.get(source.severity, 0) > severity_order.get(target.severity, 0):
            target.severity = source.severity
            target.original_severity = source.severity.value if hasattr(source.severity, "value") else str(source.severity)

        # Confidence: take highest
        if source.confidence > target.confidence:
            target.confidence = source.confidence
            target.specialist_confidence = source.specialist_confidence

        # Merge evidence items avoiding duplicates
        existing_evidence_keys = {
            (ev.type, ev.file, ev.line_start, ev.symbol) for ev in target.evidence
        }
        for ev in source.evidence:
            key = (ev.type, ev.file, ev.line_start, ev.symbol)
            if key not in existing_evidence_keys:
                target.evidence.append(ev)
                existing_evidence_keys.add(key)

        # Assign root cause ID and finding group ID
        if not target.root_cause_id:
            target.root_cause_id = f"rc-{uuid.uuid4().hex[:8]}"
        source.root_cause_id = target.root_cause_id
        if not target.finding_group_id:
            target.finding_group_id = f"grp-{uuid.uuid4().hex[:8]}"
        source.finding_group_id = target.finding_group_id

    @classmethod
    def _assign_root_causes(cls, findings: list[ReviewFinding]) -> None:
        """
        Group multiple related findings that stem from the same root cause.
        E.g. missing auth validation in service + unauthenticated endpoint in controller.
        """
        grouped_by_symbol: dict[str, list[ReviewFinding]] = {}
        for f in findings:
            key = f"{f.file_path}::{f.affected_symbol or 'global'}"
            grouped_by_symbol.setdefault(key, []).append(f)

        for _group_key, items in grouped_by_symbol.items():
            if len(items) > 1:
                root_cause_id = f"rc-{uuid.uuid4().hex[:8]}"
                finding_group_id = f"grp-{uuid.uuid4().hex[:8]}"
                for item in items:
                    item.root_cause_id = root_cause_id
                    item.finding_group_id = finding_group_id
