
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer


def serialize_utc_datetime(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


# --------------------------------------------------
# Assessment template schemas
# --------------------------------------------------

class AssessmentTemplateCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    department_id: int | None = None
    description: str | None = None
    assessment_type: str = Field(
        default="psychometric",
        pattern="^(psychometric|technical|english_grammar|logical_reasoning|programming|cognitive|composition|algorithm|comprehension)$",
    )
    assessment_tag: str = Field(
        default="Assessment",
        pattern="^(Assessment|Pre-Assessment)$",
    )
    custom_tags: list[str] = Field(default_factory=list)
    reading_passage: str | None = None

    question_count: int = Field(default=20, gt=0, le=200)
    duration_minutes: int | None = Field(default=None, ge=1, le=300)

    category_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Question categories and their distribution",
    )
    assignment_scope: str | None = Field(
        default="all",
        pattern="^(all|cohort|learner)$",
    )
    cohort_ids: list[int] = Field(default_factory=list)
    learner_ids: list[int] = Field(default_factory=list)
    due_at: datetime | None = None


class AssessmentTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    department_id: int | None = None
    department_name: str | None = None
    assessment_type: str = "psychometric"
    assessment_tag: str = "Assessment"
    custom_tags: list[str] = Field(default_factory=list)
    reading_passage: str | None = None
    description: str | None
    question_count: int
    category_config: dict[str, Any]
    is_active: bool
    created_by_user_id: int
    created_at: datetime
    duration_minutes: int = 15
    assignment_scope: str = "all"
    assigned_cohort_ids: list[int] = Field(default_factory=list)
    assigned_learner_ids: list[int] = Field(default_factory=list)
    assigned_count: int = 0
    assignment_summary: str = "All Learners"
    due_at: datetime | None = None

    @field_serializer("created_at", "due_at", mode="plain", check_fields=False)
    def serialize_template_dates(self, dt: datetime | None):
        return serialize_utc_datetime(dt)


# --------------------------------------------------
# Assessment question schemas
# --------------------------------------------------

class AssessmentOptionResponse(BaseModel):
    id: str
    text: str


class AssessmentQuestionResponse(BaseModel):
    id: int
    category: str
    question_set: str = "A"
    difficulty: str = "Medium"
    question_type: str
    question_text: str
    passage_text: str | None = None
    instructions: str | None = None
    options: list[AssessmentOptionResponse]
    display_order: int
    max_score: float = 1.0
    negative_marks: float = 0.0


# --------------------------------------------------
# Start assessment schemas
# --------------------------------------------------

class AssessmentStartRequest(BaseModel):
    template_id: int = Field(gt=0)
    force_new: bool = False


class AssessmentStartResponse(BaseModel):
    session_id: int
    status: str
    question_count: int
    duration_minutes: int = 30
    remaining_seconds: int | None = None
    started_at: datetime
    expires_at: datetime | None = None
    template_name: str | None = None
    assessment_type: str | None = None
    assessment_tag: str | None = "Assessment"
    assigned_set: str = "A"
    reading_passage: str | None = None
    questions: list[AssessmentQuestionResponse]

    @field_serializer("started_at", "expires_at", mode="plain", check_fields=False)
    def serialize_dates(self, dt: datetime | None):
        return serialize_utc_datetime(dt)


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
        max_length=100,
    )
    tab_switch_count: int | None = 0

    @field_validator("answers")
    @classmethod
    def validate_unique_questions(cls, answers):
        question_ids = [item.question_id for item in answers]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                "Duplicate answers for the same question are not allowed"
            )

        return answers


class AssessmentTabSwitchRequest(BaseModel):
    tab_switch_count: int = Field(default=0, ge=0, le=100)


class AssessmentSubmitResponse(BaseModel):
    session_id: int
    status: str
    completed_at: datetime
    message: str

    @field_serializer("completed_at", mode="plain", check_fields=False)
    def serialize_completed_at(self, dt: datetime | None):
        return serialize_utc_datetime(dt)


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
    template_id: int | None = None
    template_name: str | None = None
    assessment_type: str | None = "psychometric"
    learner_user_id: int | None = None
    learner_name: str | None = None
    learner_email: str | None = None
    status: str | None = "completed"
    completed_at: datetime | None = None
    categories: list[AssessmentCategoryScoreResponse]
    total_questions: int = 20
    answered_count: int = 0
    unanswered_count: int = 20
    total_score: float = 0
    max_score: float = 0
    overall_percentage: float = 0
    tab_switch_count: int = 0


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
    template_id: int | None = None
    template_name: str | None = None
    assessment_type: str | None = "psychometric"
    learner_user_id: int | None = None
    learner_name: str | None = None
    learner_email: str | None = None
    report_data: dict[str, Any]
    report_text: str
    ai_model: str
    generated_at: datetime


# --------------------------------------------------
# Assessment results listing schemas
# --------------------------------------------------

class UserAssessmentResultItem(BaseModel):
    session_id: int
    template_id: int | None = None
    template_name: str
    assessment_type: str
    learner_user_id: int
    learner_name: str | None = None
    learner_email: str | None = None
    status: str
    question_count: int
    total_score: float
    max_score: float
    overall_percentage: float
    started_at: datetime
    completed_at: datetime | None = None
    has_report: bool = False
    categories: list[AssessmentCategoryScoreResponse] = []
    tab_switch_count: int = 0

    @field_serializer("started_at", "completed_at", mode="plain", check_fields=False)
    def serialize_dates(self, dt: datetime | None):
        return serialize_utc_datetime(dt)


class AdminAssessmentResultItem(UserAssessmentResultItem):
    session_id: int | None = None
    started_at: datetime | None = None
    assignment_scope: str | None = None


class AdminAssessmentResultsResponse(BaseModel):
    results: list[AdminAssessmentResultItem]
    total_assessments: int
    completed_count: int
    average_score: float
    unique_learners: int
    attended_count: int = 0
    in_progress_count: int = 0
    expired_count: int = 0
    not_started_count: int = 0


# --------------------------------------------------
# Assessment session schemas
# --------------------------------------------------

class AssessmentSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int | None = None
    learner_user_id: int
    status: str
    question_count: int
    started_at: datetime
    completed_at: datetime | None



class AssessmentTemplateUpdate(BaseModel):
    assessment_type: str | None = Field(
        default=None,
        pattern="^(psychometric|technical|english_grammar|logical_reasoning|programming|cognitive|composition|algorithm|comprehension)$",
    )
    assessment_tag: str | None = Field(
        default=None,
        pattern="^(Assessment|Pre-Assessment)$",
    )
    custom_tags: list[str] | None = None
    reading_passage: str | None = None
    name: str | None = Field(default=None, min_length=3, max_length=200)
    department_id: int | None = None
    description: str | None = None
    is_active: bool | None = None
    category_config: dict[str, Any] | None = None
    question_count: int | None = Field(default=None, gt=0, le=200)
    duration_minutes: int | None = Field(default=None, ge=1, le=300)
    assignment_scope: str | None = Field(
        default=None,
        pattern="^(all|cohort|learner)$",
    )
    cohort_ids: list[int] | None = None
    learner_ids: list[int] | None = None
    due_at: datetime | None = None
    clear_due_at: bool | None = None


class AssessmentAssignmentPayload(BaseModel):
    scope: str = Field(default="all", pattern="^(all|cohort|learner)$")
    cohort_ids: list[int] = Field(default_factory=list)
    learner_ids: list[int] = Field(default_factory=list)
    due_at: datetime | None = None


class AssessmentAssignmentTargetSummary(BaseModel):
    template_id: int
    scope: str = "all"
    cohort_ids: list[int] = Field(default_factory=list)
    learner_ids: list[int] = Field(default_factory=list)
    assigned_count: int = 0
    due_at: datetime | None = None

    @field_serializer("due_at", mode="plain", check_fields=False)
    def serialize_due_at(self, dt: datetime | None):
        return serialize_utc_datetime(dt)


class AssignableCohortItem(BaseModel):
    id: int
    name: str
    status: str
    department_id: int
    member_count: int = 0


class AssignableLearnerItem(BaseModel):
    id: int
    full_name: str
    email: str
    cohort_ids: list[int] = Field(default_factory=list)


class AssignableTargetsResponse(BaseModel):
    cohorts: list[AssignableCohortItem] = Field(default_factory=list)
    learners: list[AssignableLearnerItem] = Field(default_factory=list)


class StudentAssignedAssessmentItem(BaseModel):
    template_id: int
    department_id: int | None = None
    department_name: str | None = None
    assignment_id: int | None = None
    assignment_scope: str = "all"
    cohort_name: str | None = None
    name: str
    description: str | None = None
    assessment_type: str
    assessment_tag: str = "Assessment"
    custom_tags: list[str] = Field(default_factory=list)
    category_label: str
    question_count: int
    duration_minutes: int
    status: str
    assigned_at: datetime
    due_at: datetime | None = None
    session_id: int | None = None
    started_at: datetime | None = None
    expires_at: datetime | None = None
    completed_at: datetime | None = None
    remaining_seconds: int | None = None
    total_score: float | None = None
    max_score: float | None = None
    overall_percentage: float | None = None
    has_report: bool = False
    tab_switch_count: int = 0
    can_start: bool = False
    can_continue: bool = False
    notification_title: str | None = None

    @field_serializer("assigned_at", "due_at", "started_at", "expires_at", "completed_at", mode="plain", check_fields=False)
    def serialize_item_dates(self, dt: datetime | None):
        return serialize_utc_datetime(dt)


class StudentAssignedStats(BaseModel):
    total_assigned: int = 0
    not_started_count: int = 0
    in_progress_count: int = 0
    completed_count: int = 0
    expired_count: int = 0
    average_score: float = 0.0


class StudentAssignedAssessmentsResponse(BaseModel):
    assessments: list[StudentAssignedAssessmentItem] = Field(default_factory=list)
    notifications: list[StudentAssignedAssessmentItem] = Field(default_factory=list)
    stats: StudentAssignedStats = Field(default_factory=StudentAssignedStats)
    cohort_names: list[str] = Field(default_factory=list)
    synced_at: datetime

    @field_serializer("synced_at", mode="plain", check_fields=False)
    def serialize_synced_at(self, dt: datetime | None):
        return serialize_utc_datetime(dt)


class LearnerAssessmentStatusResponse(BaseModel):
    status: str
    session_id: int | None = None
    total_assigned: int = 0
    completed_count: int = 0
    pending_count: int = 0
    all_completed: bool = False
    pre_assessments_completed: bool = False
    has_chosen_department: bool = False
    has_approved_department: bool = False
    is_activated_by_admin: bool = False
    selected_department_id: str | None = None
    department_approved: bool = False
    onboarding_stage: str = "assessment_pending"


class AssessmentResumeResponse(BaseModel):
    session_id: int
    status: str
    question_count: int
    duration_minutes: int = 30
    remaining_seconds: int | None = None
    started_at: datetime
    expires_at: datetime | None = None
    template_name: str | None = None
    assessment_type: str | None = None
    assessment_tag: str | None = "Assessment"
    assigned_set: str = "A"
    reading_passage: str | None = None
    saved_answers: dict[int, str] = Field(default_factory=dict)
    marked_for_review: list[int] = Field(default_factory=list)
    questions: list[AssessmentQuestionResponse]

    @field_serializer("started_at", "expires_at", mode="plain", check_fields=False)
    def serialize_dates(self, dt: datetime | None):
        return serialize_utc_datetime(dt)


class AssessmentSessionCheckResponse(BaseModel):
    session_id: int
    template_id: int | None = None
    template_name: str | None = None
    assessment_type: str | None = None
    assessment_tag: str | None = None
    status: str
    is_submitted: bool
    is_expired: bool
    is_in_progress: bool
    remaining_seconds: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    has_report: bool = False
    redirect_url: str | None = None

    @field_serializer("started_at", "completed_at", mode="plain", check_fields=False)
    def serialize_dates(self, dt: datetime | None):
        return serialize_utc_datetime(dt)


class AssessmentAnswerSaveRequest(BaseModel):
    question_id: int = Field(gt=0)
    answer: str | list[str] | None = None
    is_marked_for_review: bool | None = None


class AssessmentAnswerSaveResponse(BaseModel):
    status: str = "saved"
    question_id: int
    answer: str | None = None
    is_marked_for_review: bool = False


class AssessmentBankQuestionCreate(BaseModel):
    category: str = Field(min_length=2, max_length=100)
    question_set: str = Field(default="A", pattern="^[ABCabc]$")
    difficulty: str = Field(default="Medium", max_length=20)
    question_type: str = Field(default="multiple_choice", max_length=50)
    question_text: str = Field(min_length=5, max_length=3000)
    passage_text: str | None = Field(default=None, max_length=12000)
    instructions: str | None = Field(default=None, max_length=2000)
    explanation: str | None = Field(default=None, max_length=3000)
    options: list[AssessmentOptionResponse] = Field(default_factory=list, max_length=10)
    correct_option_id: str | None = Field(default=None, max_length=20)
    correct_option_ids: list[str] | None = None
    max_score: float = Field(default=1.0, gt=0, le=100)
    negative_marks: float = Field(default=0.0, ge=0, le=50)
    in_assessment: bool = True


class AssessmentBankQuestionUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=2, max_length=100)
    question_set: str | None = Field(default=None, pattern="^[ABCabc]$")
    difficulty: str | None = Field(default=None, max_length=20)
    question_type: str | None = Field(default=None, max_length=50)
    question_text: str | None = Field(default=None, min_length=5, max_length=3000)
    passage_text: str | None = Field(default=None, max_length=12000)
    instructions: str | None = Field(default=None, max_length=2000)
    explanation: str | None = Field(default=None, max_length=3000)
    options: list[AssessmentOptionResponse] | None = Field(default=None, max_length=10)
    correct_option_id: str | None = Field(default=None, max_length=20)
    correct_option_ids: list[str] | None = None
    max_score: float | None = Field(default=None, gt=0, le=100)
    negative_marks: float | None = Field(default=None, ge=0, le=50)
    in_assessment: bool | None = None


class AssessmentBankQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    category: str
    question_set: str = "A"
    difficulty: str = "Medium"
    question_type: str
    question_text: str
    passage_text: str | None = None
    instructions: str | None = None
    explanation: str | None = None
    options: list[AssessmentOptionResponse]
    max_score: float
    negative_marks: float = 0.0
    display_order: int | None = None
    in_assessment: bool = True
    is_active: bool
    correct_option_id: str | None = None
    correct_option_ids: list[str] = Field(default_factory=list)


class AssessmentBankReorderRequest(BaseModel):
    question_ids: list[int] = Field(default_factory=list)


class AssessmentPreviewQuestionItem(BaseModel):
    id: int
    source: str = "bank"
    category: str
    question_set: str = "A"
    difficulty: str = "Medium"
    question_type: str
    question_text: str
    passage_text: str | None = None
    instructions: str | None = None
    options: list[AssessmentOptionResponse]
    display_order: int
    max_score: float = 1.0
    negative_marks: float = 0.0
    correct_option_id: str | None = None
    correct_option_ids: list[str] | None = None
    explanation: str | None = None


class AssessmentTemplatePreviewResponse(BaseModel):
    template_id: int
    template_name: str
    assessment_type: str
    assessment_tag: str = "Assessment"
    assigned_set: str = "A"
    reading_passage: str | None = None
    description: str | None = None
    instructions: str
    mode: str
    duration_minutes: int
    total_questions: int
    configured_question_count: int
    custom_question_count: int
    builtin_question_count: int
    total_marks: float
    questions: list[AssessmentPreviewQuestionItem]

