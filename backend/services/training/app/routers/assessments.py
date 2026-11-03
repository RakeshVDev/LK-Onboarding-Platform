
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
ASSESSMENT_DURATION_MINUTES = 15

from services.identity.app.dependencies.auth import get_current_user
from services.identity.app.core.roles import Role

from services.training.app.db.session import SessionLocal

from services.training.app.models.assessment import (
    AssessmentTemplate,
    AssessmentSession,
    AssessmentQuestion,
    AssessmentResponse,
    AssessmentScore,
    AssessmentReport,
)

from services.training.app.schemas.assessment import (
    AssessmentTemplateCreate,
    AssessmentTemplateUpdate,
    AssessmentTemplateResponse,
    AssessmentQuestionResponse,
    AssessmentStartRequest,
    AssessmentStartResponse,
    AssessmentSubmitRequest,
    AssessmentSubmitResponse,
    AssessmentScoresResponse,
    AssessmentReportResponse,
    LearnerAssessmentStatusResponse,
)

from services.training.app.services.assessment_mock import (
    generate_mock_questions,
)
from services.training.app.services.assessment_report import (
    generate_assessment_report,
)

from services.training.app.services.assessment_scoring import (
    calculate_assessment_scores,
)


router = APIRouter(
    prefix="/assessments",
    tags=["Psychometric Assessments"],
)


CATEGORIES = {
    "personality_work_preferences": "Personality & Work Preferences",
    "logical_reasoning": "Logical Reasoning",
    "situational_judgement": "Situational Judgement",
    "emotional_intelligence": "Emotional Intelligence",
    "learning_adaptability": "Learning & Adaptability",
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def role_of(user) -> str:
    return str(user.role.value if hasattr(user.role, "value") else user.role)


def require_assessment_manager(user):
    if role_of(user) not in {
        Role.ADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Teacher can manage assessments",
        )


def validate_category_config(config: dict):
    if set(config.keys()) != set(CATEGORIES.keys()):
        raise HTTPException(
            status_code=422,
            detail="Assessment must contain exactly the five supported categories",
        )

    for category, expected_label in CATEGORIES.items():
        item = config[category]

        if not isinstance(item, dict):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid configuration for {category}",
            )

        if item.get("question_count") != 4:
            raise HTTPException(
                status_code=422,
                detail=f"{category} must contain exactly 4 questions",
            )

        if item.get("label") != expected_label:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid category label for {category}",
            )


def validate_template_settings(question_count: int, config: dict):
    if question_count != 20:
        raise HTTPException(
            status_code=422,
            detail="The current mock assessment requires exactly 20 questions",
        )

    validate_category_config(config)


# --------------------------------------------------
# Learner: Check mandatory assessment status
# --------------------------------------------------

@router.get(
    "/my/status",
    response_model=LearnerAssessmentStatusResponse,
)
def get_my_assessment_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) != Role.LEARNER.value:
        raise HTTPException(
            status_code=403,
            detail="Only learners can access their assessment status",
        )

    # Check whether the learner has already completed an assessment.
    completed_session = db.scalar(
        select(AssessmentSession)
        .where(
            AssessmentSession.learner_user_id == current_user.id,
            AssessmentSession.status == "completed",
        )
        .order_by(AssessmentSession.completed_at.desc())
    )

    if completed_session:
        return LearnerAssessmentStatusResponse(
            status="completed",
            session_id=completed_session.id,
        )

    # Check for an existing unfinished session.
    existing_session = db.scalar(
        select(AssessmentSession)
        .where(
            AssessmentSession.learner_user_id == current_user.id,
            AssessmentSession.status == "in_progress",
        )
        .order_by(AssessmentSession.started_at.desc())
    )

    if existing_session:
        return LearnerAssessmentStatusResponse(
            status="in_progress",
            session_id=existing_session.id,
        )

    return LearnerAssessmentStatusResponse(
        status="not_started",
        session_id=None,
    )


# --------------------------------------------------
# Admin: List assessment templates
# --------------------------------------------------

@router.get(
    "/templates",
    response_model=list[AssessmentTemplateResponse],
)
def list_templates(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = role_of(current_user)

    if role in {
        Role.ADMIN.value,
        Role.TEACHER.value,
    }:
        query = select(AssessmentTemplate)

    elif role == Role.LEARNER.value:
        query = select(AssessmentTemplate).where(
            AssessmentTemplate.is_active.is_(True)
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="You cannot access assessment templates",
        )

    return db.scalars(
        query.order_by(AssessmentTemplate.id.desc())
    ).all()


# --------------------------------------------------
# Admin: Create assessment template
# --------------------------------------------------

@router.post(
    "/templates",
    response_model=AssessmentTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    payload: AssessmentTemplateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)

    validate_template_settings(
        payload.question_count,
        payload.category_config,
    )

    existing = db.scalar(
        select(AssessmentTemplate).where(
            AssessmentTemplate.name == payload.name
        )
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="An assessment template with this name already exists",
        )

    template = AssessmentTemplate(
        name=payload.name,
        description=payload.description,
        question_count=payload.question_count,
        category_config=payload.category_config,
        is_active=True,
        created_by_user_id=current_user.id,
    )

    try:
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create assessment template",
        )


# --------------------------------------------------
# Admin: Update assessment template
# --------------------------------------------------

@router.put(
    "/templates/{template_id}",
    response_model=AssessmentTemplateResponse,
)
def update_template(
    template_id: int,
    payload: AssessmentTemplateUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)

    template = db.get(AssessmentTemplate, template_id)

    if template is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment template not found",
        )

    changes = payload.model_dump(exclude_unset=True)

    question_count = changes.get(
        "question_count",
        template.question_count,
    )

    category_config = changes.get(
        "category_config",
        template.category_config,
    )

    validate_template_settings(question_count, category_config)

    if "name" in changes:
        duplicate = db.scalar(
            select(AssessmentTemplate).where(
                AssessmentTemplate.name == changes["name"],
                AssessmentTemplate.id != template_id,
            )
        )

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Another template already uses this name",
            )

    for field, value in changes.items():
        setattr(template, field, value)

    try:
        db.commit()
        db.refresh(template)
        return template

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not update assessment template",
        )


# --------------------------------------------------
# Learner: Start assessment
# --------------------------------------------------

@router.post(
    "/start",
    response_model=AssessmentStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_assessment(
    payload: AssessmentStartRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) != Role.LEARNER.value:
        raise HTTPException(
            status_code=403,
            detail="Only learners can start an assessment",
        )

    template = db.get(AssessmentTemplate, payload.template_id)

    if template is None or not template.is_active:
        raise HTTPException(
            status_code=404,
            detail="Active assessment template not found",
        )

    if template.question_count != 20:
        raise HTTPException(
            status_code=400,
            detail="This assessment currently requires 20 questions",
        )

    existing_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.learner_user_id == current_user.id,
            AssessmentSession.template_id == template.id,
            AssessmentSession.status == "in_progress",
        )
    )

    if existing_session:
        raise HTTPException(
            status_code=409,
            detail=(
                "You already have an assessment in progress. "
                f"Session ID: {existing_session.id}"
            ),
        )

    questions = generate_mock_questions()

    session = AssessmentSession(
        template_id=template.id,
        learner_user_id=current_user.id,
        status="in_progress",
        question_count=len(questions),
        ai_model="mock-v1",
        prompt_version="mock-v1",
        rubric_version="mock-rubric-v1",
    )

    try:
        db.add(session)
        db.flush()

        public_questions = []

        for index, question in enumerate(questions, start=1):
            db_question = AssessmentQuestion(
                session_id=session.id,
                category=question["category"],
                question_type=question["question_type"],
                question_text=question["question_text"],
                options=question["options"],
                scoring_key=question["scoring_key"],
                display_order=index,
                max_score=question["max_score"],
            )

            db.add(db_question)
            db.flush()

            public_questions.append(
                AssessmentQuestionResponse(
                    id=db_question.id,
                    category=db_question.category,
                    question_type=db_question.question_type,
                    question_text=db_question.question_text,
                    options=db_question.options,
                    display_order=db_question.display_order,
                )
            )

        db.commit()
        db.refresh(session)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not create assessment session",
        )

    except Exception:
        db.rollback()
        raise

    return AssessmentStartResponse(
        session_id=session.id,
        status=session.status,
        question_count=session.question_count,
        started_at=session.started_at,
        questions=public_questions,
    )



# --------------------------------------------------
# Learner: Submit assessment
# --------------------------------------------------
# Learner: Submit assessment
# --------------------------------------------------

@router.post(
    "/sessions/{session_id}/submit",
    response_model=AssessmentSubmitResponse,
)
def submit_assessment(
    session_id: int,
    payload: AssessmentSubmitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) != Role.LEARNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only learners can submit assessments",
        )

    # Lock this learner's session so simultaneous submissions cannot both succeed.
    assessment_session = db.scalar(
        select(AssessmentSession)
        .where(
            AssessmentSession.id == session_id,
            AssessmentSession.learner_user_id == current_user.id,
        )
        .with_for_update()
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment session not found",
        )

    # A completed session is immutable: every later submission is rejected.
    if assessment_session.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment has already been submitted",
        )

    if assessment_session.started_at is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Assessment start time is missing",
        )

    if assessment_session.question_count != 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assessment question count",
        )

    questions = db.scalars(
        select(AssessmentQuestion)
        .where(AssessmentQuestion.session_id == session_id)
        .order_by(AssessmentQuestion.display_order)
    ).all()

    if len(questions) != 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assessment must contain exactly 20 questions",
        )

    # Compare against the timestamp saved by the backend when the session started.
    # MySQL commonly returns DATETIME columns as naive datetimes. In that case,
    # use the application's local naive clock consistently for this comparison.
    started_at = assessment_session.started_at
    if started_at.tzinfo is not None:
        now = datetime.now(started_at.tzinfo)
    else:
        now = datetime.now()

    deadline = started_at + timedelta(minutes=ASSESSMENT_DURATION_MINUTES)
    time_expired = now >= deadline

    answers = payload.answers
    answer_count = len(answers)

    # Before the deadline, the learner must submit all 20 answers.
    # At/after the deadline, any count from 0 through 20 is accepted.
    if not time_expired and answer_count != 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You must answer all 20 questions before the 15-minute deadline",
        )

    question_ids = {question.id for question in questions}
    submitted_ids = {item.question_id for item in answers}

    if len(submitted_ids) != answer_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Duplicate question answers are not allowed",
        )

    if not submitted_ids.issubset(question_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Submitted answers contain a question that does not belong to this assessment",
        )

    normalized_responses = []
    for item in answers:
        if not isinstance(item.answer, str) or not item.answer.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Every submitted answer must contain a valid option ID",
            )

        normalized_responses.append(
            {
                "question_id": item.question_id,
                "answer": item.answer.strip(),
            }
        )

    scoring_questions = [
        {
            "id": question.id,
            "category": question.category,
            "scoring_key": question.scoring_key,
            "max_score": question.max_score,
        }
        for question in questions
    ]

    try:
        # The scoring engine must score all 20 questions. Missing answers receive 0.
        result = calculate_assessment_scores(
            scoring_questions,
            normalized_responses,
        )

        question_results = {
            item["question_id"]: item
            for item in result["question_results"]
        }

        # Save only answers actually submitted by the learner.
        response_records = []
        for item in normalized_responses:
            scored = question_results[item["question_id"]]
            response_records.append(
                AssessmentResponse(
                    session_id=session_id,
                    question_id=item["question_id"],
                    answer=item["answer"],
                    points_awarded=scored["points_awarded"],
                )
            )

        if response_records:
            db.add_all(response_records)

        # Always persist all five category scores, including zero-score categories.
        score_records = [
            AssessmentScore(
                session_id=session_id,
                category=item["category"],
                score=item["score"],
                max_score=item["max_score"],
                percentage=item["percentage"],
            )
            for item in result["category_scores"]
        ]
        db.add_all(score_records)

        assessment_session.status = "completed"
        assessment_session.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(assessment_session)

        submitted_message = (
            "Assessment submitted successfully"
            if not time_expired
            else "Assessment time expired. Submitted answers were saved and unanswered questions received zero."
        )

        return AssessmentSubmitResponse(
            session_id=assessment_session.id,
            status=assessment_session.status,
            completed_at=assessment_session.completed_at,
            message=submitted_message,
        )

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assessment submission conflicts with existing records",
        )

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# Learner: View assessment results
# --------------------------------------------------

@router.get(
    "/sessions/{session_id}/results",
    response_model=AssessmentScoresResponse,
)
def get_assessment_results(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) != Role.LEARNER.value:
        raise HTTPException(
            status_code=403,
            detail="Only learners can view their assessment results",
        )

    # Verify session ownership.
    assessment_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.id == session_id,
            AssessmentSession.learner_user_id == current_user.id,
        )
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if assessment_session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Assessment has not been completed yet",
        )

    # Retrieve saved scores from MySQL.
    scores = db.scalars(
        select(AssessmentScore)
        .where(AssessmentScore.session_id == session_id)
        .order_by(AssessmentScore.category)
    ).all()

    if len(scores) != 5:
        raise HTTPException(
            status_code=404,
            detail="Assessment results are not available",
        )

    return AssessmentScoresResponse(
        session_id=session_id,
        categories=[
            {
                "category": score.category,
                "score": score.score,
                "max_score": score.max_score,
                "percentage": score.percentage,
            }
            for score in scores
        ],
    )



# --------------------------------------------------
# Learner: Generate assessment report
# --------------------------------------------------

@router.post(
    "/sessions/{session_id}/report",
    response_model=AssessmentReportResponse,
)
def create_assessment_report(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) != Role.LEARNER.value:
        raise HTTPException(
            status_code=403,
            detail="Only learners can generate their assessment reports",
        )

    # Lock the session during report creation.
    assessment_session = db.scalar(
        select(AssessmentSession)
        .where(
            AssessmentSession.id == session_id,
            AssessmentSession.learner_user_id == current_user.id,
        )
        .with_for_update()
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if assessment_session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Complete the assessment before generating a report",
        )

    # Return the existing report if already generated.
    existing_report = db.scalar(
        select(AssessmentReport).where(
            AssessmentReport.session_id == session_id
        )
    )

    if existing_report:
        return AssessmentReportResponse(
            id=existing_report.id,
            session_id=existing_report.session_id,
            report_data=existing_report.report_data,
            report_text=existing_report.report_text,
            ai_model=existing_report.ai_model,
            generated_at=existing_report.generated_at,
        )

    scores = db.scalars(
        select(AssessmentScore).where(
            AssessmentScore.session_id == session_id
        )
    ).all()

    if len(scores) != 5:
        raise HTTPException(
            status_code=404,
            detail="Five category scores are required to generate the report",
        )

    score_data = [
        {
            "category": item.category,
            "score": item.score,
            "max_score": item.max_score,
            "percentage": item.percentage,
        }
        for item in scores
    ]

    try:
        generated = generate_assessment_report(score_data)

        report = AssessmentReport(
            session_id=session_id,
            report_data=generated["report_data"],
            report_text=generated["report_text"],
            ai_model=generated["ai_model"],
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        return AssessmentReportResponse(
            id=report.id,
            session_id=report.session_id,
            report_data=report.report_data,
            report_text=report.report_text,
            ai_model=report.ai_model,
            generated_at=report.generated_at,
        )

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except IntegrityError:
        db.rollback()

        # Another request may have created the report first.
        existing_report = db.scalar(
            select(AssessmentReport).where(
                AssessmentReport.session_id == session_id
            )
        )

        if existing_report:
            return AssessmentReportResponse(
                id=existing_report.id,
                session_id=existing_report.session_id,
                report_data=existing_report.report_data,
                report_text=existing_report.report_text,
                ai_model=existing_report.ai_model,
                generated_at=existing_report.generated_at,
            )

        raise HTTPException(
            status_code=409,
            detail="Could not save the assessment report",
        )

    except Exception:
        db.rollback()
        raise


# --------------------------------------------------
# Learner: View saved assessment report
# --------------------------------------------------

@router.get(
    "/sessions/{session_id}/report",
    response_model=AssessmentReportResponse,
)
def get_assessment_report(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) != Role.LEARNER.value:
        raise HTTPException(
            status_code=403,
            detail="Only learners can view their assessment reports",
        )

    assessment_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.id == session_id,
            AssessmentSession.learner_user_id == current_user.id,
        )
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if assessment_session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Assessment has not been completed",
        )

    report = db.scalar(
        select(AssessmentReport).where(
            AssessmentReport.session_id == session_id
        )
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment report has not been generated yet",
        )

    return AssessmentReportResponse(
        id=report.id,
        session_id=report.session_id,
        report_data=report.report_data,
        report_text=report.report_text,
        ai_model=report.ai_model,
        generated_at=report.generated_at,
    )

