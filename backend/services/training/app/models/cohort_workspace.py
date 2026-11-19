"""SQLAlchemy ORM models for persistent Cohort Workspace features (curriculum, assignments, quizzes, announcements, discussions, attendance matrix, bookmarks)."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from services.training.app.db.base import Base


class CohortChapter(Base):
    __tablename__ = "cohort_chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    department_name: Mapped[str] = mapped_column(String(150), default="All / Common", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CohortLesson(Base):
    __tablename__ = "cohort_lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("cohort_chapters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cohort_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    department_name: Mapped[str] = mapped_column(String(150), default="All / Common", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    lesson_type: Mapped[str] = mapped_column(String(30), nullable=False)
    duration: Mapped[str | None] = mapped_column(String(60), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    text_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[str | None] = mapped_column(String(60), nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quiz_questions_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scheduled_date: Mapped[str | None] = mapped_column(String(80), nullable=True)
    scheduled_time: Mapped[str | None] = mapped_column(String(80), nullable=True)
    meeting_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_live_now: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trainer_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CohortAssignment(Base):
    __tablename__ = "cohort_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    department_name: Mapped[str] = mapped_column(String(150), default="All / Common", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    module: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    due_date: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    requirements_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_size: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CohortAssignmentSubmission(Base):
    __tablename__ = "cohort_assignment_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("cohort_assignments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learner_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    learner_name: Mapped[str] = mapped_column(String(150), nullable=False)
    learner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="submitted", nullable=False)
    submission_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    submission_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trainer_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("assignment_id", "learner_user_id", name="uq_cohort_assignment_submission"),
    )


class CohortQuiz(Base):
    __tablename__ = "cohort_quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    department_name: Mapped[str] = mapped_column(String(150), default="All / Common", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    module: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    questions_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    due_date: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    passing_score: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_size: Mapped[str | None] = mapped_column(String(60), nullable=True)
    questions_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CohortQuizSubmission(Base):
    __tablename__ = "cohort_quiz_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(
        ForeignKey("cohort_quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learner_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    learner_name: Mapped[str] = mapped_column(String(150), nullable=False)
    learner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    answers_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("quiz_id", "learner_user_id", name="uq_cohort_quiz_submission"),
    )


class CohortAnnouncement(Base):
    __tablename__ = "cohort_announcements"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="important", nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    author_name: Mapped[str] = mapped_column(String(150), nullable=False)
    author_role: Mapped[str] = mapped_column(String(80), default="Lead Instructor", nullable=False)
    author_avatar: Mapped[str] = mapped_column(String(10), default="TR", nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CohortAnnouncementRead(Base):
    __tablename__ = "cohort_announcement_reads"

    id: Mapped[int] = mapped_column(primary_key=True)
    announcement_id: Mapped[int] = mapped_column(
        ForeignKey("cohort_announcements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_cohort_announcement_read"),
    )


class CohortDiscussion(Base):
    __tablename__ = "cohort_discussions"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="Technical Q&A", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    author_name: Mapped[str] = mapped_column(String(150), nullable=False)
    author_role: Mapped[str] = mapped_column(String(80), nullable=False)
    author_avatar: Mapped[str] = mapped_column(String(10), default="TR", nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CohortDiscussionReply(Base):
    __tablename__ = "cohort_discussion_replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    discussion_id: Mapped[int] = mapped_column(
        ForeignKey("cohort_discussions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    author_name: Mapped[str] = mapped_column(String(150), nullable=False)
    author_role: Mapped[str] = mapped_column(String(80), nullable=False)
    author_avatar: Mapped[str] = mapped_column(String(10), default="TR", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_trainer_reply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CohortDiscussionLike(Base):
    __tablename__ = "cohort_discussion_likes"

    id: Mapped[int] = mapped_column(primary_key=True)
    discussion_id: Mapped[int] = mapped_column(
        ForeignKey("cohort_discussions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("discussion_id", "user_id", name="uq_cohort_discussion_like"),
    )


class CohortAttendanceEntry(Base):
    __tablename__ = "cohort_attendance_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    cohort_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    learner_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    attendance_date: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(4), default="P", nullable=False)
    session_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_by_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("cohort_id", "learner_user_id", "attendance_date", name="uq_cohort_attendance_day"),
    )


class CohortMaterialBookmark(Base):
    __tablename__ = "cohort_material_bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    material_key: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "material_key", name="uq_cohort_material_bookmark"),
    )
