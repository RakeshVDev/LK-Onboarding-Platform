"""FastAPI Router for Department-Gated Live Classes & Video Sessions."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.application.training.live_classes import (
    LiveClassAccessError,
    LiveClassUseCase,
    LiveClassValidationError,
)
from app.infrastructure.training.repositories import (
    SqlAlchemyLiveClassRepository,
    resolve_learner_exact_approved_department_id,
)
from app.interfaces.training.schemas import (
    AssignableHostResponse,
    LiveClassCreate,
    LiveClassJoinResponse,
    LiveClassListResponse,
    LiveClassResponse,
    LiveClassUpdate,
)
from services.identity.app.dependencies.auth import get_current_user
from services.training.app.routers.assessments import get_db
from services.training.app.services.teacher_scope import resolve_teacher_scope

router = APIRouter(
    prefix="/live-classes",
    tags=["Department-Gated Live Classes"],
)


def _role_str(user) -> str:
    return str(user.role.value if hasattr(user.role, "value") else user.role).lower()


def _use_case(db: Session) -> LiveClassUseCase:
    return LiveClassUseCase(SqlAlchemyLiveClassRepository(db))


@router.get("", response_model=LiveClassListResponse)
def list_live_classes(
    department_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = _role_str(current_user)
    approved_dept_id = (
        resolve_learner_exact_approved_department_id(db, int(current_user.id))
        if role == "learner"
        else None
    )
    sessions = _use_case(db).list_sessions(
        actor_role=role,
        learner_approved_department_id=approved_dept_id,
        requested_department_id=department_id,
        teacher_allowed_department_ids=resolve_teacher_scope(db, current_user),
    )
    restricted_reason = None
    if role == "learner" and approved_dept_id is None:
        restricted_reason = "Complete all assessments and await Admin department approval to unlock department live classes."

    return LiveClassListResponse(
        sessions=[LiveClassResponse(**asdict(s)) for s in sessions],
        approved_department_id=approved_dept_id,
        restricted_reason=restricted_reason,
    )


@router.post("", response_model=LiveClassResponse, status_code=status.HTTP_201_CREATED)
def create_live_class(
    payload: LiveClassCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        created = _use_case(db).create_session(
            actor_role=_role_str(current_user),
            actor_user_id=int(current_user.id),
            actor_name=getattr(current_user, "full_name", None),
            title=payload.title,
            description=payload.description,
            department_id=payload.department_id,
            instructor_user_id=payload.instructor_user_id,
            scheduled_start=payload.scheduled_start,
            duration_minutes=payload.duration_minutes,
            meeting_url=payload.meeting_url,
            platform=payload.platform,
            teacher_allowed_department_ids=resolve_teacher_scope(db, current_user),
        )
    except LiveClassAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LiveClassValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return LiveClassResponse(**asdict(created))


@router.get("/assignable-hosts", response_model=list[AssignableHostResponse])
def list_assignable_live_class_hosts(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        hosts = _use_case(db).list_assignable_hosts(
            actor_role=_role_str(current_user),
            actor_user_id=int(current_user.id),
            actor_name=getattr(current_user, "full_name", None),
            actor_email=getattr(current_user, "email", None),
        )
        return [
            AssignableHostResponse(
                id=h.id,
                full_name=h.full_name,
                email=h.email,
                role=h.role,
            )
            for h in hosts
        ]
    except LiveClassAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=LiveClassResponse)
def get_live_class(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = _role_str(current_user)
    approved_dept_id = (
        resolve_learner_exact_approved_department_id(db, int(current_user.id))
        if role == "learner"
        else None
    )
    try:
        session = _use_case(db).get_session_with_access_check(
            session_id=session_id,
            actor_role=role,
            learner_approved_department_id=approved_dept_id,
            teacher_allowed_department_ids=resolve_teacher_scope(db, current_user),
        )
    except LiveClassAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class session not found")

    return LiveClassResponse(**asdict(session))


@router.post("/{session_id}/join", response_model=LiveClassJoinResponse)
def join_live_class(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = _role_str(current_user)
    approved_dept_id = (
        resolve_learner_exact_approved_department_id(db, int(current_user.id))
        if role == "learner"
        else None
    )
    try:
        session = _use_case(db).join_session(
            session_id=session_id,
            actor_role=role,
            learner_approved_department_id=approved_dept_id,
            teacher_allowed_department_ids=resolve_teacher_scope(db, current_user),
        )
    except LiveClassAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LiveClassValidationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class session not found")

    return LiveClassJoinResponse(
        session_id=int(session.id),
        title=session.title,
        department_id=session.department_id,
        department_name=session.department_name,
        meeting_url=session.meeting_url,
        platform=session.platform,
        status=session.status,
    )


@router.patch("/{session_id}", response_model=LiveClassResponse)
def update_live_class(
    session_id: int,
    payload: LiveClassUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        updated = _use_case(db).update_session(
            session_id=session_id,
            actor_role=_role_str(current_user),
            actor_user_id=int(current_user.id),
            actor_name=getattr(current_user, "full_name", None),
            instructor_user_id=payload.instructor_user_id,
            title=payload.title,
            description=payload.description,
            department_id=payload.department_id,
            scheduled_start=payload.scheduled_start,
            duration_minutes=payload.duration_minutes,
            meeting_url=payload.meeting_url,
            platform=payload.platform,
            status=payload.status,
            teacher_allowed_department_ids=resolve_teacher_scope(db, current_user),
        )
    except LiveClassAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LiveClassValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class session not found")
    return LiveClassResponse(**asdict(updated))


@router.delete("/{session_id}", status_code=status.HTTP_200_OK)
def delete_live_class(
    session_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        deleted = _use_case(db).delete_session(
            session_id=session_id,
            actor_role=_role_str(current_user),
            teacher_allowed_department_ids=resolve_teacher_scope(db, current_user),
        )
    except LiveClassAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Live class session not found")
    return {"status": "deleted", "session_id": session_id}

