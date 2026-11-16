"""Pure domain entities for offline Assessment Intelligence & Comprehension analytics."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DimensionScoreEntity:
    dimension_key: str
    dimension_label: str
    normalized_score: float
    raw_score: float
    max_score: float
    percentile_band: str
    interpretation: str
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RadarAxisEntity:
    axis_key: str
    axis_label: str
    candidate_score: float
    benchmark_score: float
    cohort_average: float | None = None


@dataclass(slots=True)
class EvaluationReportEntity:
    session_id: int
    assessment_type: str
    overall_percentage: float
    scoring_version: str
    dimensions: list[DimensionScoreEntity] = field(default_factory=list)
    radar_profile: list[RadarAxisEntity] = field(default_factory=list)
    summary_narrative: str = ""

