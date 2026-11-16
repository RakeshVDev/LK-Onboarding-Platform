"""Infrastructure ORM models for Training & Department-Gated Live Classes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from services.training.app.db.base import Base as TrainingBase
from services.training.app.models.assessment import (
    AssessmentQuestion,
    AssessmentQuestionBank,
    AssessmentSession,
    AssessmentTemplate,
)
from services.training.app.models.entities import Department, StudentDepartmentRequest


class LiveClassSession(TrainingBase):
    """Scheduled or active live class / video session strictly bound to one Department."""

    __tablename__ = "live_class_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"), nullable=False, index=True
    )
    instructor_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    instructor_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    meeting_url: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str] = mapped_column(String(60), default="Video Call", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


__all__ = [
    "AssessmentQuestion",
    "AssessmentQuestionBank",
    "AssessmentSession",
    "AssessmentTemplate",
    "Department",
    "LiveClassSession",
    "StudentDepartmentRequest",
    "TrainingBase",
]

