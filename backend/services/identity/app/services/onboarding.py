from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.identity.app.core.roles import Role
from services.identity.app.models.user import User, UserDepartment
from services.identity.app.schemas.auth import UserResponse
from services.identity.app.schemas.onboarding import (
    NavItemPermission,
    NavigationPermissionsResponse,
)

COMMON_DEPARTMENT_NAME = "All / Common"

LEARNER_RESTRICTED_NAV_ITEMS: tuple[NavItemPermission, ...] = (
    NavItemPermission(key="assessment", label="Assessment", route="/my-assessments", allowed=True),
    NavItemPermission(key="result", label="Result", route="/my-results", allowed=True),
    NavItemPermission(key="report", label="Report", route="/my-reports", allowed=True),
)

LEARNER_FULL_NAV_ITEMS: tuple[NavItemPermission, ...] = (
    NavItemPermission(key="dashboard", label="Dashboard", route="/dashboard", allowed=True),
    NavItemPermission(key="courses", label="Courses", route="/courses", allowed=True),
    NavItemPermission(key="cohorts", label="Cohorts", route="/cohorts", allowed=True),
    NavItemPermission(key="assessment", label="Assessment", route="/my-assessments", allowed=True),
    NavItemPermission(key="result", label="Result", route="/my-results", allowed=True),
    NavItemPermission(key="report", label="Report", route="/my-reports", allowed=True),
    NavItemPermission(key="profile", label="Profile", route="/profile", allowed=True),
)


class TrainingOnboardingBridge(Protocol):
    """Abstraction over the training service DB for assessment & department sync."""

    def get_assessment_status(self, user_id: int) -> dict[str, Any]:
        ...

    def get_department_map(self) -> dict[str, str]:
        ...

    def get_department_by_id(self, department_id: str | int) -> dict[str, Any] | None:
        ...

    def upsert_department_request(
        self,
        user_id: int,
        department_id: int,
        notes: str | None = None,
    ) -> None:
        ...

    def approve_department_request(
        self,
        user_id: int,
        department_id: int,
        reviewer_id: int,
        notes: str | None = None,
    ) -> None:
        ...


class SqlAlchemyTrainingBridge:
    """Default bridge backed directly by the training service database."""

    def get_assessment_status(self, user_id: int) -> dict[str, Any]:
        from services.training.app.db.session import SessionLocal as TrainingSessionLocal
        from services.training.app.routers.assessments import compute_learner_assessment_status

        with TrainingSessionLocal() as tdb:
            res = compute_learner_assessment_status(tdb, user_id)
            return {
                "status": res.status,
                "total_assigned": int(res.total_assigned),
                "completed_count": int(res.completed_count),
                "pending_count": int(res.pending_count),
                "all_completed": bool(res.all_completed),
                "pre_assessments_completed": bool(res.pre_assessments_completed),
                "has_approved_department": bool(res.has_approved_department),
            }

    def get_department_map(self) -> dict[str, str]:
        try:
            from services.training.app.db.session import SessionLocal as TrainingSessionLocal
            from services.training.app.models.entities import Department

            with TrainingSessionLocal() as tdb:
                rows = tdb.query(Department.id, Department.name).all()
                return {str(row[0]): str(row[1]) for row in rows}
        except Exception:
            return {}

    def get_department_by_id(self, department_id: str | int) -> dict[str, Any] | None:
        try:
            dept_int = int(str(department_id).strip())
        except (TypeError, ValueError):
            return None

        from services.training.app.db.session import SessionLocal as TrainingSessionLocal
        from services.training.app.models.entities import Department

        with TrainingSessionLocal() as tdb:
            dept = tdb.get(Department, dept_int)
            if dept is None:
                return None
            return {
                "id": int(dept.id),
                "name": str(dept.name),
                "is_active": bool(dept.is_active),
            }

    def upsert_department_request(
        self,
        user_id: int,
        department_id: int,
        notes: str | None = None,
    ) -> None:
        from services.training.app.db.session import SessionLocal as TrainingSessionLocal
        from services.training.app.models.entities import StudentDepartmentRequest

        with TrainingSessionLocal() as tdb:
            existing_pending = (
                tdb.query(StudentDepartmentRequest)
                .filter(
                    StudentDepartmentRequest.user_id == user_id,
                    StudentDepartmentRequest.status == "pending",
                )
                .order_by(StudentDepartmentRequest.id.desc())
                .first()
            )
            if existing_pending:
                existing_pending.department_id = department_id
                existing_pending.notes = notes
            else:
                tdb.add(
                    StudentDepartmentRequest(
                        user_id=user_id,
                        department_id=department_id,
                        status="pending",
                        notes=notes,
                    )
                )
            tdb.commit()

    def approve_department_request(
        self,
        user_id: int,
        department_id: int,
        reviewer_id: int,
        notes: str | None = None,
    ) -> None:
        from services.training.app.db.session import SessionLocal as TrainingSessionLocal
        from services.training.app.models.entities import StudentDepartmentRequest

        now = datetime.now(timezone.utc)
        with TrainingSessionLocal() as tdb:
            latest_pending = (
                tdb.query(StudentDepartmentRequest)
                .filter(
                    StudentDepartmentRequest.user_id == user_id,
                    StudentDepartmentRequest.status == "pending",
                )
                .order_by(StudentDepartmentRequest.id.desc())
                .first()
            )
            if latest_pending:
                latest_pending.department_id = department_id
                latest_pending.status = "approved"
                latest_pending.reviewed_by_user_id = reviewer_id
                latest_pending.reviewed_at = now
                if notes is not None:
                    latest_pending.notes = notes
            else:
                latest_approved = (
                    tdb.query(StudentDepartmentRequest)
                    .filter(
                        StudentDepartmentRequest.user_id == user_id,
                        StudentDepartmentRequest.status == "approved",
                    )
                    .order_by(StudentDepartmentRequest.id.desc())
                    .first()
                )
                if latest_approved:
                    latest_approved.department_id = department_id
                    latest_approved.reviewed_by_user_id = reviewer_id
                    latest_approved.reviewed_at = now
                    if notes is not None:
                        latest_approved.notes = notes
                else:
                    tdb.add(
                        StudentDepartmentRequest(
                            user_id=user_id,
                            department_id=department_id,
                            status="approved",
                            notes=notes,
                            reviewed_by_user_id=reviewer_id,
                            reviewed_at=now,
                        )
                    )
            tdb.commit()


def get_training_bridge() -> TrainingOnboardingBridge:
    return SqlAlchemyTrainingBridge()


def compute_onboarding_stage(user: User) -> str:
    """Compute deterministic sequential onboarding stage for a user."""
    if user.role != Role.LEARNER.value:
        return "staff"
    if not bool(user.all_assessments_completed):
        return "assessment_pending"
    if not bool(user.is_activated_by_admin):
        return "awaiting_activation"
    if not bool(user.department_approved):
        if user.selected_department_id:
            return "department_pending_approval"
        return "department_selection"
    return "unlocked"


def get_user_assigned_departments_map(
    db: Session,
    user_ids: list[int],
) -> dict[int, list[int]]:
    clean_ids = sorted({int(uid) for uid in user_ids if uid is not None})
    if not clean_ids:
        return {}
    rows = db.scalars(
        select(UserDepartment)
        .where(UserDepartment.user_id.in_(clean_ids))
        .order_by(UserDepartment.id.asc())
    ).all()
    mapping: dict[int, list[int]] = {uid: [] for uid in clean_ids}
    for row in rows:
        mapping.setdefault(int(row.user_id), []).append(int(row.department_id))
    return mapping


def serialize_user_with_onboarding(
    user: User,
    department_map: dict[str, str] | None = None,
    assigned_dept_ids: list[int] | None = None,
    db: Session | None = None,
) -> UserResponse:
    response = UserResponse.model_validate(user)
    response.onboarding_stage = compute_onboarding_stage(user)
    if department_map and user.selected_department_id:
        response.selected_department_name = department_map.get(str(user.selected_department_id))
    if assigned_dept_ids is None and db is not None and user.role == Role.TEACHER.value:
        assigned_dept_ids = get_user_assigned_departments_map(db, [user.id]).get(user.id, [])
    dept_id_list = [int(d) for d in (assigned_dept_ids or [])]
    response.assigned_department_ids = dept_id_list
    if department_map and dept_id_list:
        response.assigned_department_names = [
            department_map.get(str(did), f"Department #{did}") for did in dept_id_list
        ]
    else:
        response.assigned_department_names = []
    return response


def validate_and_assign_teacher_departments(
    db: Session,
    target_user: User,
    department_ids: list[int],
    assigned_by_user_id: int,
    bridge: TrainingOnboardingBridge,
) -> list[int]:
    if target_user.role != Role.TEACHER.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Departments can only be assigned to teacher accounts",
        )

    clean_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in department_ids or []:
        did = int(raw_id)
        if did <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Department IDs must be positive integers",
            )
        if did not in seen:
            seen.add(did)
            clean_ids.append(did)

    if len(clean_ids) < 1 or len(clean_ids) > 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A teacher must be assigned between 1 and 8 concrete departments.",
        )

    for did in clean_ids:
        validate_selectable_department(bridge, did)

    existing_rows = db.scalars(
        select(UserDepartment).where(UserDepartment.user_id == target_user.id)
    ).all()
    for row in existing_rows:
        db.delete(row)
    db.flush()

    for did in clean_ids:
        db.add(
            UserDepartment(
                user_id=target_user.id,
                department_id=did,
                assigned_by_user_id=assigned_by_user_id,
            )
        )
    db.commit()
    return clean_ids


def sync_learner_assessments_if_completed(
    db: Session,
    user: User,
    bridge: TrainingOnboardingBridge,
) -> dict[str, Any] | None:
    """Synchronize user.all_assessments_completed bidirectionally with pending Pre-Assessments."""
    if user.role != Role.LEARNER.value:
        return None
    try:
        status_info = bridge.get_assessment_status(user.id)
    except Exception:
        return None

    if status_info.get("pre_assessments_completed") is False and bool(user.all_assessments_completed):
        user.all_assessments_completed = False
        db.commit()
        db.refresh(user)
    elif (
        not bool(user.all_assessments_completed)
        and status_info.get("all_completed") is True
        and (
            int(status_info.get("total_assigned", 0)) > 0
            or status_info.get("pre_assessments_completed") is True
        )
    ):
        user.all_assessments_completed = True
        db.commit()
        db.refresh(user)
    return status_info


def validate_selectable_department(
    bridge: TrainingOnboardingBridge,
    department_id: str | int,
) -> dict[str, Any]:
    dept = bridge.get_department_by_id(department_id)
    if dept is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )
    if not dept.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected department is inactive",
        )
    if str(dept.get("name", "")).strip().lower() in {
        COMMON_DEPARTMENT_NAME.lower(),
        "all/common",
        "common",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please choose a specialization department rather than All / Common",
        )
    return dept


def build_navigation_permissions(
    user: User,
    department_name: str | None = None,
) -> NavigationPermissionsResponse:
    stage = compute_onboarding_stage(user)
    role = user.role

    if role in {Role.SUPERADMIN.value, Role.ADMIN.value}:
        nav_items = [
            NavItemPermission(key="dashboard", label="Dashboard", route="/dashboard"),
            NavItemPermission(key="departments", label="Departments", route="/departments"),
            NavItemPermission(key="courses", label="Courses", route="/courses"),
            NavItemPermission(key="cohorts", label="Cohorts", route="/cohorts"),
            NavItemPermission(key="users", label="User Management", route="/users"),
            NavItemPermission(key="assessments", label="Assessment Admin", route="/assessments"),
            NavItemPermission(key="profile", label="Profile", route="/profile"),
        ]
        allowed_keys = [item.key for item in nav_items] + ["assessment", "result", "report"]
        return NavigationPermissionsResponse(
            role=role,
            onboarding_stage=stage,
            all_assessments_completed=bool(user.all_assessments_completed),
            is_activated_by_admin=bool(user.is_activated_by_admin),
            selected_department_id=user.selected_department_id,
            selected_department_name=department_name,
            department_approved=bool(user.department_approved),
            is_unlocked=True,
            assessment_only_mode=False,
            can_select_department=False,
            redirect_to="/dashboard",
            allowed_items=allowed_keys,
            locked_items=[],
            nav_items=nav_items,
            status_message="Full administrative navigation enabled.",
        )

    if role == Role.TEACHER.value:
        nav_items = [
            NavItemPermission(key="dashboard", label="Dashboard", route="/dashboard"),
            NavItemPermission(key="courses", label="Courses", route="/courses"),
            NavItemPermission(key="cohorts", label="Cohorts", route="/cohorts"),
            NavItemPermission(key="assessments", label="Assessments", route="/assessments"),
            NavItemPermission(key="profile", label="Profile", route="/profile"),
        ]
        return NavigationPermissionsResponse(
            role=role,
            onboarding_stage=stage,
            all_assessments_completed=bool(user.all_assessments_completed),
            is_activated_by_admin=bool(user.is_activated_by_admin),
            selected_department_id=user.selected_department_id,
            selected_department_name=department_name,
            department_approved=bool(user.department_approved),
            is_unlocked=True,
            assessment_only_mode=False,
            can_select_department=False,
            redirect_to="/dashboard",
            allowed_items=[item.key for item in nav_items],
            locked_items=["departments", "users"],
            nav_items=nav_items,
            status_message="Instructor navigation enabled.",
        )

    # Strict Learner state machine
    if stage == "unlocked":
        nav_items = [item.model_copy() for item in LEARNER_FULL_NAV_ITEMS]
        dept_label = department_name or user.selected_department_id or "your department"
        return NavigationPermissionsResponse(
            role=role,
            onboarding_stage=stage,
            all_assessments_completed=True,
            is_activated_by_admin=True,
            selected_department_id=user.selected_department_id,
            selected_department_name=department_name,
            department_approved=True,
            is_unlocked=True,
            assessment_only_mode=False,
            can_select_department=False,
            redirect_to="/dashboard",
            allowed_items=[item.key for item in nav_items],
            locked_items=["departments", "users"],
            nav_items=nav_items,
            status_message=f"Onboarding complete. Approved department: {dept_label}.",
        )

    restricted_items = [item.model_copy() for item in LEARNER_RESTRICTED_NAV_ITEMS]
    locked_for_pending = [
        "dashboard",
        "courses",
        "cohorts",
        "departments",
        "users",
        "profile",
    ]
    can_select = stage in {"department_selection", "department_pending_approval"}
    redirect_to = "/department-selection" if can_select else "/my-assessments"

    if stage == "assessment_pending":
        if bool(user.department_approved):
            msg = "A priority Pre-Assessment is pending. Complete it to unlock workspace navigation."
        else:
            msg = "Complete all assigned pre-assessments before awaiting admin activation."
    elif stage == "awaiting_activation":
        msg = "All assessments completed. Waiting for an administrator to activate your department selection."
    elif stage == "department_selection":
        msg = "Activated by admin. Choose your desired department for final approval."
    else:
        dept_label = department_name or user.selected_department_id or "Selected department"
        msg = f"{dept_label} submitted and awaiting final admin approval."

    return NavigationPermissionsResponse(
        role=role,
        onboarding_stage=stage,
        all_assessments_completed=bool(user.all_assessments_completed),
        is_activated_by_admin=bool(user.is_activated_by_admin),
        selected_department_id=user.selected_department_id,
        selected_department_name=department_name,
        department_approved=bool(user.department_approved),
        is_unlocked=False,
        assessment_only_mode=True,
        can_select_department=can_select,
        redirect_to=redirect_to,
        allowed_items=[item.key for item in restricted_items],
        locked_items=locked_for_pending,
        nav_items=restricted_items,
        status_message=msg,
    )

