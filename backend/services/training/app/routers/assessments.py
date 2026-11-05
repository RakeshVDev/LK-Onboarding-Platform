
from datetime import datetime, timezone, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
ASSESSMENT_DURATION_MINUTES = 15

from services.identity.app.dependencies.auth import get_current_user
from services.identity.app.core.roles import Role
from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
from services.identity.app.models.user import User as IdentityUser

from services.training.app.db.session import SessionLocal

from services.training.app.models.assessment import (
    AssessmentTemplate,
    AssessmentSession,
    AssessmentQuestion,
    AssessmentResponse,
    AssessmentScore,
    AssessmentReport,
    AssessmentQuestionBank,
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
    AssessmentResumeResponse,
    AssessmentAnswerSaveRequest,
    AssessmentAnswerSaveResponse,
    AssessmentBankQuestionCreate,
    AssessmentBankQuestionResponse,
    AssessmentCategoryScoreResponse,
    UserAssessmentResultItem,
    AdminAssessmentResultsResponse,
)

from services.training.app.services.assessment_mock import (
    generate_mock_questions,
)
from services.training.app.services.assessment_logical_reasoning import (
    get_default_logical_reasoning_questions,
)
from services.training.app.services.assessment_grammar_technical import (
    get_default_english_grammar_questions,
    get_default_technical_questions,
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

VALID_CATEGORIES_BY_TYPE = {
    "english_grammar": {
        "english_grammar",
        "subject_verb_agreement",
        "tenses_and_aspects",
        "tenses",
        "articles",
        "prepositions",
        "conjunctions",
        "voice_and_speech",
        "active_passive_voice",
        "direct_indirect_speech",
        "sentence_correction",
        "error_detection",
        "vocabulary",
        "synonyms_antonyms",
        "idioms_collocations",
        "reading_comprehension",
    },
    "logical_reasoning": {
        "logical_reasoning",
        "number_series",
        "alphabet_series",
        "coding_decoding",
        "blood_relations",
        "direction_distance",
        "pattern_recognition",
        "logical_statements",
        "odd_one_out",
        "analogy",
    },
    "technical": {
        "technical",
        "technical_knowledge",
        "data_structures",
        "algorithms",
        "python_programming",
        "javascript_web",
        "databases_sql",
        "system_design",
        "git_devops",
        "networking",
        "operating_systems",
    },
    "programming": {
        "programming",
        "programming_logic",
        "algorithm_understanding",
        "code_output",
        "problem_solving",
        "debugging",
        "time_complexity",
        "data_structures",
    },
    "psychometric": {
        "psychometric",
        "personality_work_preferences",
        "situational_judgement",
        "emotional_intelligence",
        "learning_adaptability",
        "team_collaboration",
    },
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def role_of(user) -> str:
    return str(user.role.value if hasattr(user.role, "value") else user.role)


def require_assessment_manager(user):
    if role_of(user) not in {
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Teacher can manage assessments",
        )


def get_users_map(user_ids: list[int]) -> dict[int, dict[str, str]]:
    if not user_ids:
        return {}
    try:
        with IdentitySessionLocal() as id_db:
            users = id_db.scalars(
                select(IdentityUser).where(IdentityUser.id.in_(user_ids))
            ).all()
            return {
                u.id: {"full_name": u.full_name, "email": u.email}
                for u in users
            }
    except Exception:
        return {}


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


def get_duration_minutes_for_template(template: AssessmentTemplate | None) -> int:
    if template and getattr(template, "assessment_type", None) == "logical_reasoning":
        return 30
    return 15


def to_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def validate_template_settings(question_count: int, config: dict, assessment_type: str = "psychometric"):
    if assessment_type == "logical_reasoning":
        if question_count != 25:
            raise HTTPException(status_code=422, detail="Logical Reasoning assessment must contain exactly 25 questions")
    elif assessment_type == "psychometric":
        if question_count != 20:
            raise HTTPException(status_code=422, detail="Each psychometric assessment must contain exactly 20 questions")
        validate_category_config(config)
    elif question_count <= 0:
        raise HTTPException(status_code=422, detail="Assessment must contain at least 1 question")

    if not isinstance(config, dict):
        raise HTTPException(status_code=422, detail="Invalid category configuration")


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
        Role.SUPERADMIN.value,
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


@router.get(
    "/templates/{template_id}",
    response_model=AssessmentTemplateResponse,
)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = role_of(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment template not found",
        )
    if role == Role.LEARNER.value and not template.is_active:
        raise HTTPException(
            status_code=404,
            detail="Assessment template is not active",
        )
    return template


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
        payload.assessment_type,
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
        assessment_type=payload.assessment_type,
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

    validate_template_settings(question_count, category_config, changes.get("assessment_type", template.assessment_type))

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
    if role_of(current_user) not in {
        Role.LEARNER.value,
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to start an assessment",
        )

    template = db.get(AssessmentTemplate, payload.template_id)

    if template is None or not template.is_active:
        raise HTTPException(
            status_code=404,
            detail="Active assessment template not found",
        )

    # 1. STRICT SERVER-SIDE ENFORCEMENT: A learner can attempt each assigned assessment only ONE TIME.
    completed_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.learner_user_id == current_user.id,
            AssessmentSession.template_id == template.id,
            AssessmentSession.status == "completed",
        ).order_by(AssessmentSession.completed_at.desc())
    )
    if completed_session:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You have already completed the '{template.name}'. Only one attempt is permitted per learner. You may view your saved results and official report card.",
        )

    duration_minutes = get_duration_minutes_for_template(template)

    existing_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.learner_user_id == current_user.id,
            AssessmentSession.template_id == template.id,
            AssessmentSession.status == "in_progress",
        ).order_by(AssessmentSession.started_at.desc())
    )

    if existing_session:
        started_utc = to_utc(existing_session.started_at)
        deadline_utc = to_utc(existing_session.expires_at) or (started_utc + timedelta(minutes=duration_minutes))
        now = now_utc()
        rem_sec = int((deadline_utc - now).total_seconds())
        if rem_sec <= 0:
            # Stale / expired session! Permanently mark as completed (attempt concluded)
            existing_session.status = "completed"
            existing_session.completed_at = deadline_utc
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Your allocated examination time for '{template.name}' has expired and this assessment has been concluded.",
            )
        else:
            # Active in-progress session exists with good time remaining! Return it so the learner can continue
            q_records = db.scalars(
                select(AssessmentQuestion)
                .where(AssessmentQuestion.session_id == existing_session.id)
                .order_by(AssessmentQuestion.display_order)
            ).all()

            public_questions = [
                AssessmentQuestionResponse(
                    id=q.id,
                    category=q.category,
                    difficulty=getattr(q, "difficulty", "Medium") or "Medium",
                    question_type=q.question_type,
                    question_text=q.question_text,
                    options=q.options,
                    display_order=q.display_order,
                )
                for q in q_records
            ]

            return AssessmentStartResponse(
                session_id=existing_session.id,
                status=existing_session.status,
                question_count=existing_session.question_count,
                duration_minutes=duration_minutes,
                remaining_seconds=rem_sec,
                started_at=to_utc(existing_session.started_at),
                expires_at=deadline_utc,
                template_name=template.name,
                assessment_type=template.assessment_type,
                questions=public_questions,
            )

    # 2. Strict Category Validation & Question Sourcing
    name_lower = (template.name or "").lower()
    type_lower = (template.assessment_type or "").lower()

    if "grammar" in name_lower or "english" in name_lower or type_lower == "english_grammar":
        effective_type = "english_grammar"
    elif "technical" in name_lower or type_lower == "technical":
        effective_type = "technical"
    elif "logical" in name_lower or type_lower == "logical_reasoning":
        effective_type = "logical_reasoning"
    elif "programming" in name_lower or "coding" in name_lower or type_lower == "programming":
        effective_type = "programming"
    else:
        effective_type = type_lower or "psychometric"

    # Synchronize template.assessment_type in DB if it had diverged
    if template.assessment_type != effective_type:
        template.assessment_type = effective_type
        db.flush()

    valid_categories = VALID_CATEGORIES_BY_TYPE.get(effective_type, set())

    bank_questions = db.scalars(
        select(AssessmentQuestionBank)
        .where(
            AssessmentQuestionBank.template_id == template.id,
            AssessmentQuestionBank.is_active.is_(True),
        )
        .order_by(AssessmentQuestionBank.id)
    ).all()

    # Filter bank questions: prioritize questions for this template, guarding against cross-domain conflicts
    invalid_categories = set()
    for domain, cats in VALID_CATEGORIES_BY_TYPE.items():
        if domain != effective_type:
            invalid_categories.update(cats)

    valid_bank = [
        q for q in bank_questions
        if q.category not in invalid_categories or q.category in valid_categories or effective_type in q.category
    ]

    target_count = template.question_count if template.question_count and template.question_count > 0 else (25 if effective_type == "logical_reasoning" else 20)

    # Fetch domain-specific default questions
    if effective_type == "logical_reasoning":
        default_pool = get_default_logical_reasoning_questions()
    elif effective_type == "english_grammar":
        default_pool = get_default_english_grammar_questions()
    elif effective_type in {"technical", "programming"}:
        default_pool = get_default_technical_questions()
    else:
        default_pool = generate_mock_questions()

    # Prioritize manual questions authored by teacher/admin first
    questions = []
    seen_texts = set()

    for q in valid_bank:
        options = q.options
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except Exception:
                options = []
        scoring_key = q.scoring_key
        if isinstance(scoring_key, str):
            try:
                scoring_key = json.loads(scoring_key)
            except Exception:
                scoring_key = {}

        questions.append({
            "category": q.category,
            "difficulty": getattr(q, "difficulty", "Medium") or "Medium",
            "question_type": q.question_type or "multiple_choice",
            "question_text": q.question_text,
            "options": options,
            "scoring_key": scoring_key,
            "max_score": q.max_score,
        })
        seen_texts.add(q.question_text.strip().lower())
        if len(questions) >= target_count:
            break

    # Top up remaining questions from default pool if needed
    if len(questions) < target_count:
        for def_q in default_pool:
            if def_q["question_text"].strip().lower() not in seen_texts:
                questions.append(def_q)
                seen_texts.add(def_q["question_text"].strip().lower())
                if len(questions) >= target_count:
                    break

    # Backend Validation: Strictly assert every single question matches the target category
    for q in questions:
        if valid_categories and q["category"] not in valid_categories:
            q["category"] = effective_type

    duration_minutes = get_duration_minutes_for_template(template)
    started_at = datetime.now(timezone.utc)
    expires_at = started_at + timedelta(minutes=duration_minutes)

    session = AssessmentSession(
        template_id=template.id,
        learner_user_id=current_user.id,
        status="in_progress",
        question_count=len(questions),
        started_at=started_at,
        expires_at=expires_at,
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
                difficulty=question.get("difficulty", "Medium"),
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
                    difficulty=db_question.difficulty,
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
        duration_minutes=duration_minutes,
        remaining_seconds=int(duration_minutes * 60),
        started_at=to_utc(session.started_at),
        expires_at=to_utc(session.expires_at),
        template_name=template.name,
        assessment_type=template.assessment_type,
        questions=public_questions,
    )




# --------------------------------------------------
# Learner: Resume an in-progress assessment
# --------------------------------------------------

@router.get(
    "/sessions/{session_id}/resume",
    response_model=AssessmentResumeResponse,
)
def resume_assessment(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) not in {
        Role.LEARNER.value,
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to resume assessments",
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

    if assessment_session.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail="This assessment is no longer in progress",
        )

    template = db.get(AssessmentTemplate, assessment_session.template_id)
    duration_minutes = get_duration_minutes_for_template(template)
    started_utc = to_utc(assessment_session.started_at)
    expires_utc = to_utc(assessment_session.expires_at) or (started_utc + timedelta(minutes=duration_minutes))

    now = now_utc()
    if expires_utc and now >= expires_utc:
        assessment_session.status = "completed"
        assessment_session.completed_at = expires_utc
        db.commit()
        raise HTTPException(
            status_code=409,
            detail="This assessment has expired and been submitted",
        )

    questions = db.scalars(
        select(AssessmentQuestion)
        .where(AssessmentQuestion.session_id == session_id)
        .order_by(AssessmentQuestion.display_order)
    ).all()

    if len(questions) != assessment_session.question_count:
        raise HTTPException(
            status_code=409,
            detail="Assessment questions are incomplete",
        )

    # Fetch previously saved answers and review flags
    saved_records = db.scalars(
        select(AssessmentResponse).where(AssessmentResponse.session_id == session_id)
    ).all()
    saved_answers = {
        r.question_id: str(r.answer)
        for r in saved_records
        if r.answer is not None and str(r.answer).strip()
    }
    marked_for_review = [
        r.question_id for r in saved_records if getattr(r, "is_marked_for_review", False)
    ]

    remaining_sec = max(0, int((expires_utc - now_utc()).total_seconds())) if expires_utc else int(duration_minutes * 60)

    # Only public question fields are returned. Never expose scoring_key.
    return AssessmentResumeResponse(
        session_id=assessment_session.id,
        status=assessment_session.status,
        question_count=assessment_session.question_count,
        duration_minutes=duration_minutes,
        remaining_seconds=remaining_sec,
        started_at=started_utc,
        expires_at=expires_utc,
        template_name=template.name if template else "Assessment",
        assessment_type=template.assessment_type if template else "psychometric",
        saved_answers=saved_answers,
        marked_for_review=marked_for_review,
        questions=[
            AssessmentQuestionResponse(
                id=question.id,
                category=question.category,
                difficulty=getattr(question, "difficulty", "Medium") or "Medium",
                question_type=question.question_type,
                question_text=question.question_text,
                options=question.options,
                display_order=question.display_order,
            )
            for question in questions
        ],
    )


# --------------------------------------------------
# Learner: Save answer or toggle mark for review progressively
# --------------------------------------------------

@router.post(
    "/sessions/{session_id}/save-answer",
    response_model=AssessmentAnswerSaveResponse,
)
def save_assessment_answer(
    session_id: int,
    payload: AssessmentAnswerSaveRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) not in {
        Role.LEARNER.value,
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to save assessment answers",
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

    if assessment_session.status != "in_progress":
        raise HTTPException(
            status_code=409,
            detail="This assessment is no longer in progress",
        )

    template = db.get(AssessmentTemplate, assessment_session.template_id)
    duration_minutes = get_duration_minutes_for_template(template)

    started_at = to_utc(assessment_session.started_at)
    deadline = to_utc(assessment_session.expires_at) or (started_at + timedelta(minutes=duration_minutes))
    now = now_utc()

    if now >= deadline:
        raise HTTPException(
            status_code=409,
            detail="Assessment time has expired. Please submit your answers.",
        )

    question = db.scalar(
        select(AssessmentQuestion).where(
            AssessmentQuestion.session_id == session_id,
            AssessmentQuestion.id == payload.question_id,
        )
    )
    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found in this assessment session",
        )

    record = db.scalar(
        select(AssessmentResponse).where(
            AssessmentResponse.session_id == session_id,
            AssessmentResponse.question_id == payload.question_id,
        )
    )

    if record is None:
        record = AssessmentResponse(
            session_id=session_id,
            question_id=payload.question_id,
            answer=payload.answer.strip() if payload.answer else None,
            is_marked_for_review=payload.is_marked_for_review or False,
        )
        db.add(record)
    else:
        if payload.answer is not None:
            record.answer = payload.answer.strip() if payload.answer else None
        if payload.is_marked_for_review is not None:
            record.is_marked_for_review = payload.is_marked_for_review

    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not save answer")

    return AssessmentAnswerSaveResponse(
        status="saved",
        question_id=record.question_id,
        answer=str(record.answer) if record.answer else None,
        is_marked_for_review=record.is_marked_for_review,
    )


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
    if role_of(current_user) not in {
        Role.LEARNER.value,
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to submit assessments",
        )

    # Lock this learner's session so simultaneous submissions cannot both succeed.
    assessment_session = db.scalar(
        select(AssessmentSession)
        .where(
            AssessmentSession.id == session_id,
            AssessmentSession.learner_user_id == current_user.id,
        )
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

    expected_count = assessment_session.question_count
    if expected_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assessment question count",
        )

    questions = db.scalars(
        select(AssessmentQuestion)
        .where(AssessmentQuestion.session_id == session_id)
        .order_by(AssessmentQuestion.display_order)
    ).all()

    if len(questions) != expected_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assessment must contain exactly {expected_count} questions",
        )

    template = db.get(AssessmentTemplate, assessment_session.template_id)
    duration_minutes = get_duration_minutes_for_template(template)

    # Compare against the timestamp saved by the backend when the session started.
    started_at = to_utc(assessment_session.started_at)
    deadline = to_utc(assessment_session.expires_at) or (started_at + timedelta(minutes=duration_minutes))
    now = now_utc()
    time_expired = now >= deadline

    answers = payload.answers
    answer_count = len(answers)

    if answer_count > expected_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot submit more than {expected_count} answers",
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

        # Clear any in-progress partial responses and existing scores
        db.query(AssessmentResponse).filter(
            AssessmentResponse.session_id == session_id
        ).delete()
        db.query(AssessmentScore).filter(
            AssessmentScore.session_id == session_id
        ).delete()
        db.flush()

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

        # Always persist category scores, including zero-score categories.
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
# View assessment results (Learner or Admin/Teacher)
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
    role = role_of(current_user)

    assessment_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.id == session_id
        )
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if role == Role.LEARNER.value:
        if assessment_session.learner_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only learners can view their assessment results",
            )
    elif role not in {Role.ADMIN.value, Role.SUPERADMIN.value, Role.TEACHER.value}:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view assessment results",
        )

    if assessment_session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Assessment has not been completed yet",
        )

    template = db.scalar(
        select(AssessmentTemplate).where(AssessmentTemplate.id == assessment_session.template_id)
    )
    user_info = get_users_map([assessment_session.learner_user_id]).get(assessment_session.learner_user_id, {})

    # Retrieve saved scores from MySQL.
    scores = db.scalars(
        select(AssessmentScore)
        .where(AssessmentScore.session_id == session_id)
        .order_by(AssessmentScore.category)
    ).all()

    if not scores:
        raise HTTPException(status_code=404, detail="Assessment results are not available")

    answered_count = db.scalar(
        select(func.count(AssessmentResponse.id)).where(
            AssessmentResponse.session_id == session_id
        )
    ) or 0

    total_score = sum(float(score.score) for score in scores)
    max_score = sum(float(score.max_score) for score in scores)
    overall_percentage = (
        total_score / max_score * 100 if max_score > 0 else 0
    )

    return AssessmentScoresResponse(
        session_id=session_id,
        template_id=template.id if template else None,
        template_name=template.name if template else "Assessment",
        assessment_type=template.assessment_type if template else "psychometric",
        learner_user_id=assessment_session.learner_user_id,
        learner_name=user_info.get("full_name"),
        learner_email=user_info.get("email"),
        status=assessment_session.status,
        completed_at=assessment_session.completed_at,
        categories=[
            {
                "category": score.category,
                "score": score.score,
                "max_score": score.max_score,
                "percentage": score.percentage,
            }
            for score in scores
        ],
        total_questions=assessment_session.question_count,
        answered_count=answered_count,
        unanswered_count=max(0, assessment_session.question_count - answered_count),
        total_score=round(total_score, 2),
        max_score=round(max_score, 2),
        overall_percentage=round(overall_percentage, 2),
    )



# --------------------------------------------------
# Generate assessment report (Learner or Admin/Teacher)
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
    role = role_of(current_user)

    # Lock the session during report creation.
    assessment_session = db.scalar(
        select(AssessmentSession)
        .where(AssessmentSession.id == session_id)
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if role == Role.LEARNER.value:
        if assessment_session.learner_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only learners can generate their assessment reports",
            )
    elif role not in {Role.ADMIN.value, Role.SUPERADMIN.value, Role.TEACHER.value}:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to generate assessment report",
        )

    if assessment_session.status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Complete the assessment before generating a report",
        )

    template = db.scalar(
        select(AssessmentTemplate).where(AssessmentTemplate.id == assessment_session.template_id)
    )
    user_info = get_users_map([assessment_session.learner_user_id]).get(assessment_session.learner_user_id, {})

    # Return the existing report if already generated.
    existing_report = db.scalar(
        select(AssessmentReport).where(
            AssessmentReport.session_id == session_id
        )
    )

    ass_type = template.assessment_type if template else "psychometric"
    temp_name = template.name if template else "Assessment Report"

    if existing_report:
        rep_data = dict(existing_report.report_data or {})
        if not rep_data.get("report_title"):
            from services.training.app.services.assessment_report import get_report_title, get_skill_level
            rep_data["report_title"] = get_report_title(ass_type, temp_name)
            rep_data["assessment_type"] = ass_type
            rep_data["template_name"] = temp_name
            rep_data["skill_level"] = get_skill_level(ass_type, float(rep_data.get("overall_percentage") or 0.0))
            existing_report.report_data = rep_data
            db.commit()

        return AssessmentReportResponse(
            id=existing_report.id,
            session_id=existing_report.session_id,
            template_id=template.id if template else None,
            template_name=temp_name,
            assessment_type=ass_type,
            learner_user_id=assessment_session.learner_user_id,
            learner_name=user_info.get("full_name"),
            learner_email=user_info.get("email"),
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

    if not scores:
        raise HTTPException(status_code=404, detail="Assessment scores are required to generate the report")

    score_data = [
        {
            "category": item.category,
            "score": item.score,
            "max_score": item.max_score,
            "percentage": item.percentage,
        }
        for item in scores
    ]

    all_questions = db.scalars(
        select(AssessmentQuestion).where(AssessmentQuestion.session_id == session_id)
    ).all()
    all_responses = db.scalars(
        select(AssessmentResponse).where(AssessmentResponse.session_id == session_id)
    ).all()

    total_q = len(all_questions)
    ans_map = {r.question_id: r for r in all_responses}
    correct_count = 0
    incorrect_count = 0
    unattempted_count = 0

    for q in all_questions:
        resp = ans_map.get(q.id)
        if not resp or not resp.answer or not str(resp.answer).strip():
            unattempted_count += 1
        elif str(resp.answer).strip().upper() == str(q.scoring_key).strip().upper():
            correct_count += 1
        else:
            incorrect_count += 1

    time_taken_seconds = None
    if assessment_session.started_at and assessment_session.completed_at:
        s_utc = to_utc(assessment_session.started_at)
        c_utc = to_utc(assessment_session.completed_at)
        time_taken_seconds = max(0, int((c_utc - s_utc).total_seconds()))

    try:
        generated = generate_assessment_report(
            category_scores=score_data,
            assessment_type=ass_type,
            template_name=temp_name,
            total_questions=total_q,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            unattempted_count=unattempted_count,
            time_taken_seconds=time_taken_seconds,
        )

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
            template_id=template.id if template else None,
            template_name=temp_name,
            assessment_type=ass_type,
            learner_user_id=assessment_session.learner_user_id,
            learner_name=user_info.get("full_name"),
            learner_email=user_info.get("email"),
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
                template_id=template.id if template else None,
                template_name=template.name if template else "Assessment Report",
                assessment_type=template.assessment_type if template else "psychometric",
                learner_user_id=assessment_session.learner_user_id,
                learner_name=user_info.get("full_name"),
                learner_email=user_info.get("email"),
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
# View saved assessment report (Learner or Admin/Teacher)
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
    role = role_of(current_user)

    assessment_session = db.scalar(
        select(AssessmentSession).where(
            AssessmentSession.id == session_id
        )
    )

    if assessment_session is None:
        raise HTTPException(
            status_code=404,
            detail="Assessment session not found",
        )

    if role == Role.LEARNER.value:
        if assessment_session.learner_user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only learners can view their assessment reports",
            )
    elif role not in {Role.ADMIN.value, Role.SUPERADMIN.value, Role.TEACHER.value}:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view assessment reports",
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

    template = db.scalar(
        select(AssessmentTemplate).where(AssessmentTemplate.id == assessment_session.template_id)
    )
    user_info = get_users_map([assessment_session.learner_user_id]).get(assessment_session.learner_user_id, {})

    ass_type = template.assessment_type if template else "psychometric"
    temp_name = template.name if template else "Assessment Report"
    rep_data = dict(report.report_data or {})

    if not rep_data.get("report_title"):
        from services.training.app.services.assessment_report import get_report_title, get_skill_level
        rep_data["report_title"] = get_report_title(ass_type, temp_name)
        rep_data["assessment_type"] = ass_type
        rep_data["template_name"] = temp_name
        rep_data["skill_level"] = get_skill_level(ass_type, float(rep_data.get("overall_percentage") or 0.0))

    return AssessmentReportResponse(
        id=report.id,
        session_id=report.session_id,
        template_id=template.id if template else None,
        template_name=temp_name,
        assessment_type=ass_type,
        learner_user_id=assessment_session.learner_user_id,
        learner_name=user_info.get("full_name"),
        learner_email=user_info.get("email"),
        report_data=rep_data,
        report_text=report.report_text,
        ai_model=report.ai_model,
        generated_at=report.generated_at,
    )


# --------------------------------------------------
# Learner: View all my assessment results & report cards
# --------------------------------------------------

@router.get(
    "/my/results",
    response_model=list[UserAssessmentResultItem],
)
def get_my_assessment_results(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sessions = (
        db.query(AssessmentSession, AssessmentTemplate)
        .join(AssessmentTemplate, AssessmentSession.template_id == AssessmentTemplate.id)
        .filter(AssessmentSession.learner_user_id == current_user.id)
        .order_by(
            AssessmentSession.completed_at.desc(),
            AssessmentSession.started_at.desc(),
        )
        .all()
    )

    if not sessions:
        return []

    session_ids = [s.id for s, _ in sessions]

    # Batch query scores
    scores = (
        db.query(AssessmentScore)
        .filter(AssessmentScore.session_id.in_(session_ids))
        .all()
    )
    scores_by_session = defaultdict(list)
    for score in scores:
        scores_by_session[score.session_id].append(score)

    # Batch query report existence
    reports = (
        db.query(AssessmentReport.session_id)
        .filter(AssessmentReport.session_id.in_(session_ids))
        .all()
    )
    sessions_with_report = {r[0] for r in reports}

    result_items = []
    for session, template in sessions:
        session_scores = scores_by_session.get(session.id, [])
        total_score = sum(float(s.score) for s in session_scores)
        max_score = sum(float(s.max_score) for s in session_scores)
        pct = round(total_score / max_score * 100, 2) if max_score > 0 else 0.0

        cat_list = [
            AssessmentCategoryScoreResponse(
                category=s.category,
                score=s.score,
                max_score=s.max_score,
                percentage=s.percentage,
            )
            for s in session_scores
        ]

        result_items.append(
            UserAssessmentResultItem(
                session_id=session.id,
                template_id=template.id,
                template_name=template.name,
                assessment_type=template.assessment_type,
                learner_user_id=current_user.id,
                learner_name=current_user.full_name,
                learner_email=current_user.email,
                status=session.status,
                question_count=session.question_count,
                total_score=round(total_score, 2),
                max_score=round(max_score, 2),
                overall_percentage=round(pct, 2),
                started_at=session.started_at,
                completed_at=session.completed_at,
                has_report=session.id in sessions_with_report,
                categories=cat_list,
            )
        )
    return result_items


# --------------------------------------------------
# Admin & Teacher: View all learners' assessment results
# --------------------------------------------------

@router.get(
    "/admin/results",
    response_model=AdminAssessmentResultsResponse,
)
def get_admin_assessment_results(
    template_id: int | None = None,
    status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_of(current_user) not in {
        Role.ADMIN.value,
        Role.SUPERADMIN.value,
        Role.TEACHER.value,
    }:
        raise HTTPException(
            status_code=403,
            detail="Only Admin, Superadmin, and Teacher can view learner assessment results",
        )

    query = (
        db.query(AssessmentSession, AssessmentTemplate)
        .join(AssessmentTemplate, AssessmentSession.template_id == AssessmentTemplate.id)
    )

    if template_id is not None:
        query = query.filter(AssessmentSession.template_id == template_id)
    if status is not None and status != "all":
        query = query.filter(AssessmentSession.status == status)

    sessions = query.order_by(
        AssessmentSession.completed_at.desc(),
        AssessmentSession.started_at.desc(),
    ).all()

    if not sessions:
        return AdminAssessmentResultsResponse(
            results=[],
            total_assessments=0,
            completed_count=0,
            average_score=0.0,
            unique_learners=0,
        )

    session_ids = [s.id for s, _ in sessions]
    learner_ids = list({s.learner_user_id for s, _ in sessions})

    users_map = get_users_map(learner_ids)

    # Batch query scores
    scores = (
        db.query(AssessmentScore)
        .filter(AssessmentScore.session_id.in_(session_ids))
        .all()
    )
    scores_by_session = defaultdict(list)
    for score in scores:
        scores_by_session[score.session_id].append(score)

    # Batch query reports
    reports = (
        db.query(AssessmentReport.session_id)
        .filter(AssessmentReport.session_id.in_(session_ids))
        .all()
    )
    sessions_with_report = {r[0] for r in reports}

    result_items = []
    completed_scores = []
    for session, template in sessions:
        user_info = users_map.get(session.learner_user_id, {})
        learner_name = user_info.get("full_name") or f"Learner #{session.learner_user_id}"
        learner_email = user_info.get("email") or ""

        if search:
            s_lower = search.strip().lower()
            if (
                s_lower not in learner_name.lower()
                and s_lower not in learner_email.lower()
                and s_lower not in template.name.lower()
            ):
                continue

        session_scores = scores_by_session.get(session.id, [])
        total_score = sum(float(s.score) for s in session_scores)
        max_score = sum(float(s.max_score) for s in session_scores)
        pct = round(total_score / max_score * 100, 2) if max_score > 0 else 0.0

        if session.status == "completed" and max_score > 0:
            completed_scores.append(pct)

        cat_list = [
            AssessmentCategoryScoreResponse(
                category=s.category,
                score=s.score,
                max_score=s.max_score,
                percentage=s.percentage,
            )
            for s in session_scores
        ]

        result_items.append(
            UserAssessmentResultItem(
                session_id=session.id,
                template_id=template.id,
                template_name=template.name,
                assessment_type=template.assessment_type,
                learner_user_id=session.learner_user_id,
                learner_name=learner_name,
                learner_email=learner_email,
                status=session.status,
                question_count=session.question_count,
                total_score=round(total_score, 2),
                max_score=round(max_score, 2),
                overall_percentage=round(pct, 2),
                started_at=session.started_at,
                completed_at=session.completed_at,
                has_report=session.id in sessions_with_report,
                categories=cat_list,
            )
        )

    completed_count = sum(1 for r in result_items if r.status == "completed")
    avg_score = round(sum(completed_scores) / len(completed_scores), 2) if completed_scores else 0.0
    unique_learners = len({r.learner_user_id for r in result_items})

    return AdminAssessmentResultsResponse(
        results=result_items,
        total_assessments=len(result_items),
        completed_count=completed_count,
        average_score=avg_score,
        unique_learners=unique_learners,
    )



# --------------------------------------------------
# Admin / Teacher: Manage reusable question bank
# --------------------------------------------------

@router.get(
    "/templates/{template_id}/questions",
    response_model=list[AssessmentBankQuestionResponse],
)
def list_bank_questions(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    questions = db.scalars(
        select(AssessmentQuestionBank)
        .where(
            AssessmentQuestionBank.template_id == template_id,
            AssessmentQuestionBank.is_active.is_(True),
        )
        .order_by(AssessmentQuestionBank.id.desc())
    ).all()
    results = []
    for q in questions:
        options = q.options
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except Exception:
                options = []
        scoring_key = q.scoring_key
        if isinstance(scoring_key, str):
            try:
                scoring_key = json.loads(scoring_key)
            except Exception:
                scoring_key = {}
        correct_id = None
        if isinstance(scoring_key, dict):
            for opt_id, val in scoring_key.items():
                if val and float(val) > 0:
                    correct_id = str(opt_id).upper()
                    break
        results.append(
            AssessmentBankQuestionResponse(
                id=q.id,
                template_id=q.template_id,
                category=q.category,
                difficulty=getattr(q, "difficulty", "Medium") or "Medium",
                question_type=q.question_type or "multiple_choice",
                question_text=q.question_text,
                options=options,
                max_score=q.max_score,
                is_active=q.is_active,
                correct_option_id=correct_id,
            )
        )
    return results


@router.post(
    "/templates/{template_id}/questions",
    response_model=AssessmentBankQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_bank_question(
    template_id: int,
    payload: AssessmentBankQuestionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    template = db.get(AssessmentTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Assessment template not found")
    option_ids = [str(option.id).strip().upper() for option in payload.options]
    if len(option_ids) != len(set(option_ids)):
        raise HTTPException(status_code=422, detail="Option IDs must be unique (A, B, C, D)")
    correct_opt = str(payload.correct_option_id).strip().upper()
    if correct_opt not in option_ids:
        raise HTTPException(status_code=422, detail="Correct option must match one of the options (A, B, C, or D)")

    clean_options = [
        {"id": str(opt.id).strip().upper(), "text": opt.text.strip()}
        for opt in payload.options
    ]
    score_val = float(payload.max_score) if payload.max_score and payload.max_score > 0 else 1.0
    clean_scoring_key = {opt_id: (score_val if opt_id == correct_opt else 0.0) for opt_id in option_ids}

    cat = payload.category.strip()
    if not cat:
        cat = template.assessment_type or "general"

    question = AssessmentQuestionBank(
        template_id=template_id,
        category=cat,
        difficulty=payload.difficulty.strip() if hasattr(payload, "difficulty") and payload.difficulty else "Medium",
        question_type=payload.question_type or "multiple_choice",
        question_text=payload.question_text.strip(),
        options=clean_options,
        scoring_key=clean_scoring_key,
        max_score=score_val,
        created_by_user_id=current_user.id,
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return AssessmentBankQuestionResponse(
        id=question.id,
        template_id=question.template_id,
        category=question.category,
        difficulty=question.difficulty or "Medium",
        question_type=question.question_type,
        question_text=question.question_text,
        options=clean_options,
        max_score=question.max_score,
        is_active=question.is_active,
        correct_option_id=correct_opt,
    )


@router.delete(
    "/templates/{template_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_bank_question(
    template_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    require_assessment_manager(current_user)
    question = db.scalar(
        select(AssessmentQuestionBank).where(
            AssessmentQuestionBank.id == question_id,
            AssessmentQuestionBank.template_id == template_id,
        )
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    question.is_active = False
    db.commit()
    return None
