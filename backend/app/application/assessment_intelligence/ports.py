"""Application ports for Assessment Intelligence evaluation."""

from __future__ import annotations

from typing import Protocol

from app.domain.assessment_intelligence import EvaluationReportEntity


class IntelligenceEvaluationPort(Protocol):
    def evaluate_session(self, session_id: int) -> EvaluationReportEntity:
        ...

