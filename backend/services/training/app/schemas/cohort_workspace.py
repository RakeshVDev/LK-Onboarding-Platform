"""Pydantic request and response schemas for persistent Cohort Workspace endpoints."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class ChapterCreateRequest(BaseModel):
    cohort_id: int | None = None
    department_id: int | None = None
    department_name: str = "All / Common"
    title: str = Field(min_length=1, max_length=255)


class LessonCreateRequest(BaseModel):
    cohort_id: int | None = None
    department_id: int | None = None
    department_name: str | None = None
    title: str = Field(min_length=1, max_length=255)
    type: Literal["video", "text", "download", "quiz", "live", "assignment"]
    duration: str | None = None
    description: str | None = None
    video_url: str | None = None
    text_notes: str | None = None
    download_url: str | None = None
    file_size: str | None = None
    file_name: str | None = None
    scheduled_date: str | None = None
    scheduled_time: str | None = None
    meeting_url: str | None = None
    is_live_now: bool = False
    trainer: str | None = None
    quiz_questions_count: int | None = None
    points: int | None = None


class AssignmentCreateRequest(BaseModel):
    cohort_id: int | None = None
    department_id: int | None = None
    department_name: str = "All / Common"
    title: str = Field(min_length=1, max_length=255)
    module: str = ""
    description: str = ""
    points: int = Field(default=100, ge=1, le=10000)
    due_date: str = ""
    requirements: list[str] = Field(default_factory=list)


class AssignmentSubmitRequest(BaseModel):
    submission_url: str = Field(min_length=1, max_length=1000)
    submission_notes: str = ""


class AssignmentGradeRequest(BaseModel):
    learner_user_id: int | None = None
    score: int = Field(ge=0, le=10000)
    feedback: str = ""


class QuizQuestionInput(BaseModel):
    id: int
    text: str
    options: list[str]
    correctIndex: int = 0
    explanation: str = ""


class QuizCreateRequest(BaseModel):
    cohort_id: int | None = None
    department_id: int | None = None
    department_name: str = "All / Common"
    title: str = Field(min_length=1, max_length=255)
    module: str = ""
    questions_count: int = Field(default=5, ge=1, le=200)
    duration_minutes: int = Field(default=15, ge=1, le=600)
    passing_score: int = Field(default=70, ge=0, le=100)
    due_date: str = "Scheduled by Instructor"
    questions: list[QuizQuestionInput] | None = None


class QuizSubmitRequest(BaseModel):
    answers: dict[int, int] = Field(default_factory=dict)


class AnnouncementCreateRequest(BaseModel):
    cohort_id: int | None = None
    department_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    priority: Literal["urgent", "important", "notice"] = "important"
    is_pinned: bool = False
    tags: list[str] = Field(default_factory=list)


class DiscussionCreateRequest(BaseModel):
    cohort_id: int | None = None
    department_id: int | None = None
    title: str = Field(min_length=1, max_length=255)
    category: Literal[
        "Technical Q&A", "Assignments", "General", "Resources", "Project Squads"
    ] = "Technical Q&A"
    content: str = Field(min_length=1)


class DiscussionReplyCreateRequest(BaseModel):
    content: str = Field(min_length=1)


class AttendanceToggleRequest(BaseModel):
    cohort_id: int | None = None
    learner_user_id: int
    date_str: str = Field(min_length=8, max_length=20)
    status: Literal["P", "A", "L", "H"] | None = None


class AttendanceBulkRequest(BaseModel):
    cohort_id: int | None = None
    date_str: str = Field(min_length=8, max_length=20)
    status: Literal["P", "A", "L", "H"]
    learner_user_ids: list[int] | None = None


class AttendanceCheckInRequest(BaseModel):
    cohort_id: int | None = None
    session_title: str | None = None


class BookmarkToggleRequest(BaseModel):
    material_key: str = Field(min_length=1, max_length=120)


class WorkspaceResponse(BaseModel):
    curriculum: list[dict[str, Any]]
    assignments: list[dict[str, Any]]
    quizzes: list[dict[str, Any]]
    announcements: list[dict[str, Any]]
    discussions: list[dict[str, Any]]
    attendance: dict[str, Any]
    attendanceMatrix: dict[str, Any]
    progress: dict[str, Any]
    bookmarkedMaterialKeys: list[str]
    deliveredMaterials: list[dict[str, Any]] = Field(default_factory=list)
