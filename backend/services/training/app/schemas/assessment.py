
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --------------------------------------------------
# Assessment template schemas
# --------------------------------------------------

class AssessmentTemplateCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    description: str | None = None

    question_count: int = Field(default=20, gt=0, le=100)

    category_config: dict[str, Any] = Field(
        description="Question categories and their distribution"
    )


class AssessmentTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    question_count: int
    category_config: dict[str, Any]
    is_active: bool
    created_by_user_id: int
    created_at: datetime


# --------------------------------------------------
# Assessment question schemas
# --------------------------------------------------

class AssessmentOptionResponse(BaseModel):
    id: str
    text: str


class AssessmentQuestionResponse(BaseModel):
    id: int
    category: str
    question_type: str
    question_text: str
    options: list[AssessmentOptionResponse]
    display_order: int


# --------------------------------------------------
# Start assessment schemas
# --------------------------------------------------

class AssessmentStartRequest(BaseModel):
    template_id: int = Field(gt=0)


class AssessmentStartResponse(BaseModel):
    session_id: int
    status: str
    question_count: int
    started_at: datetime
    questions: list[AssessmentQuestionResponse]


# --------------------------------------------------
# Student answer submission schemas
# --------------------------------------------------

class AssessmentAnswerSubmit(BaseModel):
    question_id: int = Field(gt=0)

    # Supports option IDs, text answers and structured answers.
    answer: Any


class AssessmentSubmitRequest(BaseModel):
    answers: list[AssessmentAnswerSubmit] = Field(
        min_length=0,
        max_length=20,
    )

    @field_validator("answers")
    @classmethod
    def validate_unique_questions(cls, answers):
        question_ids = [item.question_id for item in answers]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                "Duplicate answers for the same question are not allowed"
            )

        return answers


class AssessmentSubmitResponse(BaseModel):
    session_id: int
    status: str
    completed_at: datetime
    message: str


# --------------------------------------------------
# Assessment score schemas
# --------------------------------------------------

class AssessmentCategoryScoreResponse(BaseModel):
    category: str
    score: float
    max_score: float
    percentage: float


class AssessmentScoresResponse(BaseModel):
    session_id: int
    categories: list[AssessmentCategoryScoreResponse]


# --------------------------------------------------
# AI assessment report schemas
# --------------------------------------------------

class AssessmentReportData(BaseModel):
    summary: str
    strengths: list[str]
    development_areas: list[str]
    recommendations: list[str]
    category_interpretations: dict[str, str]


class AssessmentReportResponse(BaseModel):
    id: int
    session_id: int
    report_data: dict[str, Any]
    report_text: str
    ai_model: str
    generated_at: datetime


# --------------------------------------------------
# Assessment session schemas
# --------------------------------------------------

class AssessmentSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    learner_user_id: int
    status: str
    question_count: int
    started_at: datetime
    completed_at: datetime | None



class AssessmentTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = None
    is_active: bool | None = None
    category_config: dict[str, Any] | None = None
    question_count: int | None = Field(default=None, gt=0, le=100)


class LearnerAssessmentStatusResponse(BaseModel):
    status: str
    session_id: int | None = None


class AssessmentResumeResponse(BaseModel):
    session_id: int
    status: str
    question_count: int
    started_at: datetime
    questions: list[AssessmentQuestionResponse]