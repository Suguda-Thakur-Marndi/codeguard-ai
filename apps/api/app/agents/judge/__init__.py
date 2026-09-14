"""Adversarial Judge module for Phase 4 verification."""

from app.agents.judge.adversarial_judge import AdversarialJudge
from app.agents.judge.confidence import ConfidencePolicy
from app.agents.judge.deduplication import DeduplicationEngine
from app.agents.judge.schemas import (
    BatchJudgeOutput,
    FinalFindingDecision,
    JudgeDecision,
    JudgeDecisionType,
)

__all__ = [
    "AdversarialJudge",
    "JudgeDecisionType",
    "JudgeDecision",
    "FinalFindingDecision",
    "BatchJudgeOutput",
    "ConfidencePolicy",
    "DeduplicationEngine",
]
