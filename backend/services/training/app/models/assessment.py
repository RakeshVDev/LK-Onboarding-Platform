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


class AssessmentTemplate(Base):
    __tablename__ = "assessment_templates"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    assessment_type: Mapped[str] = mapped_column(String(40), default="psychometric", nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    question_count: Mapped[int] = mapped_column(
        Integer, default=20, nullable=False
    )

    # Defines categories, question distribution and assessment settings.
    category_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    created_by_user_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "question_count > 0",
            name="ck_assessment_template_question_count",
        ),
    )


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)

    template_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_templates.id"),
        nullable=False,
        index=True,
    )

    # Identity user ID is an external reference.
    learner_user_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(
        String(30), default="in_progress", nullable=False, index=True
    )

    question_count: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Keep model and prompt versions for reproducibility.
    ai_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    prompt_version: Mapped[str] = mapped_column(
        String(50), default="v1", nullable=False
    )

    rubric_version: Mapped[str] = mapped_column(
        String(50), default="v1", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "question_count > 0",
            name="ck_assessment_session_question_count",
        ),
    )


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[int] = mapped_column(primary_key=True)

    session_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    difficulty: Mapped[str] = mapped_column(
        String(20), default="Medium", nullable=False
    )

    question_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    question_text: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    # Public question choices. The API may expose these.
    options: Mapped[list] = mapped_column(
        JSON, nullable=False
    )

    # Private server-side scoring configuration.
    # Never include this field in student API responses.
    scoring_key: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )

    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False
    )

    max_score: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "display_order",
            name="uq_assessment_question_order",
        ),
        CheckConstraint(
            "display_order > 0",
            name="ck_assessment_question_order",
        ),
        CheckConstraint(
            "max_score >= 0",
            name="ck_assessment_question_max_score",
        ),
    )


class AssessmentResponse(Base):
    __tablename__ = "assessment_responses"

    id: Mapped[int] = mapped_column(primary_key=True)

    session_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Supports selected options, text answers or structured responses.
    answer: Mapped[dict | list | str | None] = mapped_column(
        JSON, nullable=True
    )

    is_marked_for_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Calculated by the backend, never accepted from the student.
    points_awarded: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "question_id",
            name="uq_assessment_response_question",
        ),
    )


class AssessmentScore(Base):
    __tablename__ = "assessment_scores"

    id: Mapped[int] = mapped_column(primary_key=True)

    session_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    score: Mapped[float] = mapped_column(
        Float, nullable=False
    )

    max_score: Mapped[float] = mapped_column(
        Float, nullable=False
    )

    percentage: Mapped[float] = mapped_column(
        Float, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "category",
            name="uq_assessment_score_category",
        ),
        CheckConstraint(
            "score >= 0 AND max_score >= 0",
            name="ck_assessment_score_nonnegative",
        ),
        CheckConstraint(
            "percentage >= 0 AND percentage <= 100",
            name="ck_assessment_score_percentage",
        ),
    )


class AssessmentReport(Base):
    __tablename__ = "assessment_reports"

    id: Mapped[int] = mapped_column(primary_key=True)

    session_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Structured AI report: strengths, development areas,
    # recommendations and category interpretations.
    report_data: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )

    report_text: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    ai_model: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class AssessmentQuestionBank(Base):
    """Reusable, manager-authored questions. Scoring keys remain server-side."""
    __tablename__ = "assessment_question_bank"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="Medium", nullable=False)
    question_type: Mapped[str] = mapped_column(String(50), default="multiple_choice", nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSON, nullable=False)
    scoring_key: Mapped[dict] = mapped_column(JSON, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("max_score > 0", name="ck_assessment_bank_max_score"),
    )
