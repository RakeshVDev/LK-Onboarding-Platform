"""FastAPI Router for Assessment Intelligence & Radar Analytics."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from services.assessment_intelligence.engine import intelligence_engine
from services.assessment_intelligence.schemas import (
    AskReportQuestionRequest,
    AskReportQuestionResponse,
    AssessmentIntelligenceResponse,
    EvaluateSessionRequest,
    OverviewAnalyticsResponse,
)
from services.identity.app.core.roles import Role
from services.identity.app.dependencies.auth import get_current_user
from services.training.app.db.session import SessionLocal
from services.training.app.models.assessment import AssessmentSession, AssessmentTemplate
from services.training.app.services.teacher_scope import (
    get_common_department_ids,
    get_teacher_assigned_dept_ids,
    require_teacher_department_access,
)


router = APIRouter(
    prefix="/assessment-intelligence",
    tags=["Assessment Intelligence & Analytics"],
)

MANAGER_ROLES = {
    Role.SUPERADMIN.value,
    Role.ADMIN.value,
    Role.TEACHER.value,
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


def _role_of(user) -> str:
    return str(user.role.value if hasattr(user.role, "value") else user.role).lower().strip()


@router.post(
    "/sessions/{session_id}/evaluate",
    response_model=AssessmentIntelligenceResponse,
)
def evaluate_session_intelligence(
    session_id: int,
    payload: EvaluateSessionRequest | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = _role_of(current_user)
    session = db.get(AssessmentSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment session not found")

    if role == Role.LEARNER.value:
        if session.learner_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to evaluate another learner's session")
    elif role not in MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    if role == Role.TEACHER.value:
        tpl = db.get(AssessmentTemplate, session.template_id) if session.template_id else None
        eff_dept = tpl.department_id if tpl else getattr(session, "department_id_snapshot", None)
        require_teacher_department_access(db, current_user, eff_dept, allow_common_read=True)

    req = payload or EvaluateSessionRequest()
    force = bool(req.force) and role in MANAGER_ROLES

    try:
        return intelligence_engine.evaluate_session(
            db,
            session_id=session_id,
            force=force,
            scoring_version_tag=req.scoring_version_tag if role in MANAGER_ROLES else None,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/sessions/{session_id}/intelligence",
    response_model=AssessmentIntelligenceResponse,
)
def get_session_intelligence(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = _role_of(current_user)
    session = db.get(AssessmentSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment session not found")

    if role == Role.LEARNER.value:
        if session.learner_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to inspect another learner's intelligence report")
    elif role not in MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    if role == Role.TEACHER.value:
        tpl = db.get(AssessmentTemplate, session.template_id) if session.template_id else None
        eff_dept = tpl.department_id if tpl else getattr(session, "department_id_snapshot", None)
        require_teacher_department_access(db, current_user, eff_dept, allow_common_read=True)

    try:
        return intelligence_engine.get_session_intelligence(db, session_id=session_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/sessions/{session_id}/ask",
    response_model=AskReportQuestionResponse,
)
def ask_session_report_assistant(
    session_id: int,
    payload: AskReportQuestionRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = _role_of(current_user)
    session = db.get(AssessmentSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment session not found")

    if role == Role.LEARNER.value:
        if session.learner_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to query another learner's report",
            )
    elif role not in MANAGER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    if role == Role.TEACHER.value:
        tpl = db.get(AssessmentTemplate, session.template_id) if session.template_id else None
        eff_dept = tpl.department_id if tpl else getattr(session, "department_id_snapshot", None)
        require_teacher_department_access(db, current_user, eff_dept, allow_common_read=True)

    try:
        return intelligence_engine.answer_session_question(
            db,
            session_id=session_id,
            question=payload.question,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get(
    "/analytics/overview",
    response_model=OverviewAnalyticsResponse,
)
def get_analytics_overview(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if _role_of(current_user) not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, SuperAdmin, and Teacher can access intelligence analytics",
        )
    try:
        from services.training.app.routers.assessments import purge_expired_assessments

        purge_expired_assessments(db)
    except Exception:
        pass
    role = _role_of(current_user)
    if role == Role.TEACHER.value:
        return intelligence_engine.get_overview_analytics(
            db,
            teacher_allowed_dept_ids=get_teacher_assigned_dept_ids(db, int(current_user.id)),
            common_dept_ids=get_common_department_ids(db),
        )
    return intelligence_engine.get_overview_analytics(db)

