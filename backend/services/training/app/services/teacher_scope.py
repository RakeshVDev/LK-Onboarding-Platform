"""Shared teacher multi-department scoping helpers across Training endpoints."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.identity.app.core.roles import Role
from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
from services.identity.app.models.user import UserDepartment
from services.training.app.models.entities import Department

COMMON_DEPARTMENT_NAMES = {"all / common", "all/common", "common"}


def role_str(user) -> str:
    raw = user.role.value if hasattr(user.role, "value") else user.role
    return str(raw).lower().strip()


def get_common_department_ids(db: Session) -> set[int]:
    rows = db.scalars(select(Department)).all()
    return {
        int(d.id)
        for d in rows
        if (d.name or "").strip().lower() in COMMON_DEPARTMENT_NAMES
    }


def is_common_department_id(db: Session, department_id: int | None) -> bool:
    if department_id is None:
        return True
    return int(department_id) in get_common_department_ids(db)


def get_teacher_assigned_dept_ids(
    db: Session,
    user_id: int,
    *,
    identity_session_factory=None,
) -> set[int]:
    """Return concrete active department IDs assigned by SuperAdmin to this teacher."""
    session_cls = identity_session_factory or IdentitySessionLocal
    try:
        with session_cls() as id_db:
            raw_ids = [
                int(did)
                for did in id_db.scalars(
                    select(UserDepartment.department_id).where(
                        UserDepartment.user_id == int(user_id)
                    )
                ).all()
            ]
    except Exception:
        return set()

    if not raw_ids:
        return set()

    common_ids = get_common_department_ids(db)
    active_ids = {
        int(d.id)
        for d in db.scalars(
            select(Department).where(
                Department.id.in_(raw_ids),
                Department.is_active == True,  # noqa: E712
            )
        ).all()
        if int(d.id) not in common_ids
    }
    return active_ids


def resolve_teacher_scope(
    db: Session,
    current_user,
    *,
    identity_session_factory=None,
) -> set[int] | None:
    """Return assigned dept IDs set when caller is teacher, else None (unrestricted staff)."""
    if role_str(current_user) != Role.TEACHER.value:
        return None
    return get_teacher_assigned_dept_ids(
        db,
        int(current_user.id),
        identity_session_factory=identity_session_factory,
    )


def require_teacher_department_access(
    db: Session,
    current_user,
    department_id: int | None,
    *,
    allow_common_read: bool = False,
    identity_session_factory=None,
) -> set[int] | None:
    """Enforce teacher access to an exact assigned department (with optional All/Common read)."""
    allowed = resolve_teacher_scope(
        db,
        current_user,
        identity_session_factory=identity_session_factory,
    )
    if allowed is None:
        return None

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No departments have been assigned to your teacher account yet. Contact a SuperAdmin.",
        )

    if allow_common_read and is_common_department_id(db, department_id):
        return allowed

    if department_id is None or int(department_id) not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access or manage resources within your assigned departments.",
        )

    return allowed
