"""Pure domain entities & value objects for Training, Multi-Set Assessments, Ingestion, and Live Classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AssessmentTag(str, Enum):
    ASSESSMENT = "Assessment"
    PRE_ASSESSMENT = "Pre-Assessment"


class QuestionSetCode(str, Enum):
    SET_A = "A"
    SET_B = "B"
    SET_C = "C"


class DifficultyLevel(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class QuestionFormat(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_SELECT = "multiple_select"
    TRUE_FALSE = "true_false"
    LIKERT = "likert"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    COMPOSITION = "composition"
    CODE_SUBMISSION = "code_submission"


class LiveClassStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class DepartmentEntity:
    id: int
    name: str
    description: str | None = None
    is_active: bool = True


@dataclass(slots=True)
class ParsedQuestionCandidate:
    row_number: int
    question_text: str
    category: str
    difficulty: str = "Medium"
    question_type: str = "multiple_choice"
    question_set: str = "A"
    options: list[dict[str, str]] = field(default_factory=list)
    correct_option_ids: list[str] = field(default_factory=list)
    scoring_key: dict[str, Any] = field(default_factory=dict)
    max_score: float = 1.0
    negative_marks: float = 0.0
    instructions: str | None = None
    explanation: str | None = None
    passage_text: str | None = None
    auto_categorized: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class IngestionRowIssue:
    row_number: int
    valid: bool
    question_preview: str
    category: str | None = None
    question_set: str = "A"
    difficulty: str = "Medium"
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bank_question_id: int | None = None


@dataclass(slots=True)
class IngestionSummary:
    filename: str
    file_format: str
    template_id: int | None
    dry_run: bool
    total_detected: int
    valid_count: int
    inserted_count: int
    failed_count: int
    items: list[IngestionRowIssue] = field(default_factory=list)
    detected_categories: dict[str, int] = field(default_factory=dict)
    detected_sets: dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class LiveClassSessionEntity:
    id: int | None
    title: str
    department_id: int
    instructor_user_id: int | None
    scheduled_start: datetime
    duration_minutes: int
    meeting_url: str
    description: str | None = None
    instructor_name: str | None = None
    department_name: str | None = None
    platform: str = "Video Call"
    status: str = LiveClassStatus.SCHEDULED.value
    ended_at: datetime | None = None
    reopen_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None



@dataclass(slots=True)
class AssignableHostEntity:
    """Active staff member eligible to host or teach a live class session."""

    id: int
    full_name: str
    email: str
    role: str
