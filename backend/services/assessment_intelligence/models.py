"""SQLAlchemy ORM models owned by Assessment Intelligence.

Models inherit from the Training service DeclarativeBase so foreign keys cleanly
reference `assessment_sessions.id` and `assessment_templates.id` across MSSQL,
MySQL, and SQLite.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from services.training.app.db.base import Base


class ScoringVersion(Base):
    """Immutable versioned scoring weights and difficulty rules."""

    __tablename__ = "scoring_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version_tag: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    assessment_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    weights_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    thresholds_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CandidateDimensionScore(Base):
    """Normalized 0-100 multi-dimensional score vector per evaluated assessment session."""

    __tablename__ = "candidate_dimension_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("assessment_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    learner_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scoring_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("scoring_versions.id"),
        nullable=True,
        index=True,
    )
    assessment_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    dimension_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dimension_label: Mapped[str] = mapped_column(String(150), nullable=False)
    raw_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    normalized_score: Mapped[float] = mapped_column(Float, nullable=False)
    percentile_band: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "dimension_key",
            name="uq_candidate_dimension_session_key",
        ),
        CheckConstraint(
            "normalized_score >= 0 AND normalized_score <= 100",
            name="ck_candidate_dim_normalized_range",
        ),
    )

