"""Pydantic request/response contracts for Question Ingestion and Department-Gated Live Classes."""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_serializer


def _serialize_utc(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


class BulkQuestionItemResult(BaseModel):
    row_number: int
    valid: bool
    question_preview: str
    category: str | None = None
    question_set: str = "A"
    difficulty: str = "Medium"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    bank_question_id: int | None = None


class BulkQuestionImportResponse(BaseModel):
    filename: str
    file_format: str
    template_id: int | None = None
    dry_run: bool = False
    total_detected: int
    valid_count: int
    inserted_count: int
    failed_count: int
    detected_categories: dict[str, int] = Field(default_factory=dict)
    detected_sets: dict[str, int] = Field(default_factory=dict)
    items: list[BulkQuestionItemResult] = Field(default_factory=list)


class LiveClassCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    department_id: int = Field(gt=0)
    instructor_user_id: int | None = Field(default=None, gt=0)
    scheduled_start: datetime
    duration_minutes: int = Field(default=60, gt=0, le=480)
    meeting_url: str = Field(min_length=5, max_length=500)
    platform: str = Field(default="Video Call", max_length=60)


class LiveClassUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    department_id: int | None = Field(default=None, gt=0)
    instructor_user_id: int | None = Field(default=None, gt=0)
    scheduled_start: datetime | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=480)
    meeting_url: str | None = Field(default=None, min_length=5, max_length=500)
    platform: str | None = Field(default=None, max_length=60)
    status: str | None = Field(default=None, pattern="^(scheduled|live|completed|cancelled)$")


class LiveClassResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    department_id: int
    department_name: str | None = None
    instructor_user_id: int
    instructor_name: str | None = None
    scheduled_start: datetime
    duration_minutes: int
    meeting_url: str
    platform: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("scheduled_start", "created_at", "updated_at", mode="plain", check_fields=False)
    def serialize_dt(self, dt: datetime | None):
        return _serialize_utc(dt)


class LiveClassListResponse(BaseModel):
    sessions: list[LiveClassResponse] = Field(default_factory=list)
    approved_department_id: int | None = None
    restricted_reason: str | None = None


class LiveClassJoinResponse(BaseModel):
    session_id: int
    title: str
    department_id: int
    department_name: str | None = None
    meeting_url: str
    platform: str
    status: str



class AssignableHostResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
