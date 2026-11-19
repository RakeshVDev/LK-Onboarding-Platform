"""Pydantic v2 API contracts for Assessment Intelligence endpoints."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_serializer


def serialize_utc_dt(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


class DimensionScoreItem(BaseModel):
    dimension_key: str
    dimension_label: str
    raw_score: float
    max_score: float
    normalized_score: float
    percentile_band: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class RadarAxisPoint(BaseModel):
    axis_key: str
    axis_label: str
    candidate_score: float
    benchmark_score: float = 75.0
    cohort_average: float | None = None


class EvaluateSessionRequest(BaseModel):
    force: bool = False
    scoring_version_tag: str | None = None


class AskReportQuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class AskReportQuestionResponse(BaseModel):
    answer: str
    intent: str
    referenced_topics: list[str] = Field(default_factory=list)
    follow_up_prompts: list[str] = Field(default_factory=list)


class AssessmentIntelligenceResponse(BaseModel):
    session_id: int
    template_id: int | None = None
    template_name: str
    assessment_type: str
    learner_user_id: int
    learner_name: str | None = None
    learner_email: str | None = None
    scoring_version: str
    overall_percentage: float
    weighted_percentage: float
    total_score: float
    max_score: float
    skill_level: str
    evaluated_at: datetime
    dimensions: list[DimensionScoreItem] = Field(default_factory=list)
    radar_profile: list[RadarAxisPoint] = Field(default_factory=list)
    domain_analysis: dict[str, Any] = Field(default_factory=dict)
    report_data: dict[str, Any] = Field(default_factory=dict)
    report_text: str = ""

    @field_serializer("evaluated_at", mode="plain", check_fields=False)
    def serialize_eval_dt(self, dt: datetime | None):
        return serialize_utc_dt(dt)


class DomainAverageSummary(BaseModel):
    assessment_type: str
    evaluated_sessions: int
    average_percentage: float
    min_percentage: float
    max_percentage: float


class AnalyticsCandidateOption(BaseModel):
    session_id: int
    learner_user_id: int
    learner_name: str
    learner_email: str = ""
    template_id: int | None = None
    template_name: str
    assessment_type: str
    overall_percentage: float
    completed_at: datetime | None = None

    @field_serializer("completed_at", mode="plain", check_fields=False)
    def serialize_completed(self, dt: datetime | None):
        return serialize_utc_dt(dt)


class OverviewAnalyticsResponse(BaseModel):
    total_evaluated_sessions: int = 0
    unique_evaluated_learners: int = 0
    global_average_percentage: float = 0.0
    domain_summaries: list[DomainAverageSummary] = Field(default_factory=list)
    evaluated_candidates: list[AnalyticsCandidateOption] = Field(default_factory=list)
    active_scoring_versions: list[dict[str, Any]] = Field(default_factory=list)

