
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.identity.app.core.security import hash_password
from services.identity.app.core.roles import Role
from services.identity.app.dependencies.auth import get_current_user, get_db
from services.identity.app.models.user import User
from services.identity.app.schemas.auth import UserResponse
from services.identity.app.schemas.users import (
    TeacherDepartmentsUpdateRequest,
    UserCreateRequest,
    UserStatusUpdateRequest,
)
from services.identity.app.services.onboarding import (
    TrainingOnboardingBridge,
    get_training_bridge,
    get_user_assigned_departments_map,
    serialize_user_with_onboarding,
    sync_learner_assessments_if_completed,
    validate_and_assign_teacher_departments,
)

router = APIRouter(prefix="/api/v1/users", tags=["User Management"])


def ensure_user_manager(current_user: User) -> None:
    if current_user.role not in {
        Role.SUPERADMIN.value,
        Role.ADMIN.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage users",
        )


def ensure_role_assignment_allowed(
    current_user: User,
    target_role: str,
) -> None:
    if target_role == Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin accounts cannot be created through this endpoint",
        )

    if (
        current_user.role == Role.ADMIN.value
        and target_role == Role.ADMIN.value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a Superadmin can create Admin accounts",
        )


@router.get("", response_model=list[UserResponse])
def list_users(
    search: str = Query(default="", max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    ensure_user_manager(current_user)

    statement = select(User)

    # Admins can manage ordinary accounts only.
    if current_user.role == Role.ADMIN.value:
        statement = statement.where(
            User.role.in_([
                Role.TEACHER.value,
                Role.LEARNER.value,
            ])
        )

    search = search.strip()
    if search:
        pattern = f"%{search}%"
        statement = statement.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.role.ilike(pattern),
            )
        )

    users = list(
        db.scalars(
            statement.order_by(User.created_at.desc(), User.id.desc())
        ).all()
    )
    for u in users:
        if u.role == Role.LEARNER.value and not bool(u.all_assessments_completed):
            sync_learner_assessments_if_completed(db, u, bridge)
    dept_map = bridge.get_department_map()
    assigned_map = get_user_assigned_departments_map(
        db, [u.id for u in users if u.role == Role.TEACHER.value]
    )
    return [
        serialize_user_with_onboarding(
            u,
            dept_map,
            assigned_dept_ids=assigned_map.get(u.id, []),
        )
        for u in users
    ]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    ensure_user_manager(current_user)
    ensure_role_assignment_allowed(current_user, payload.role)

    if payload.assigned_department_ids:
        if current_user.role != Role.SUPERADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a SuperAdmin can assign departments to teachers",
            )
        if payload.role != Role.TEACHER.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Departments can only be assigned when creating a teacher",
            )

    email = payload.email.strip().lower()

    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    assigned_ids: list[int] = []
    if payload.role == Role.TEACHER.value and payload.assigned_department_ids:
        try:
            assigned_ids = validate_and_assign_teacher_departments(
                db=db,
                target_user=user,
                department_ids=payload.assigned_department_ids,
                assigned_by_user_id=current_user.id,
                bridge=bridge,
            )
        except HTTPException:
            db.delete(user)
            db.commit()
            raise

    dept_map = bridge.get_department_map() if assigned_ids else None
    return serialize_user_with_onboarding(user, dept_map, assigned_dept_ids=assigned_ids)


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    ensure_user_manager(current_user)

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot change your own account status",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if (
        current_user.role == Role.ADMIN.value
        and user.role not in {
            Role.TEACHER.value,
            Role.LEARNER.value,
        }
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins can manage Teacher and Learner accounts only",
        )

    if (
        user.role == Role.SUPERADMIN.value
        and not payload.is_active
    ):
        active_superadmins = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role == Role.SUPERADMIN.value,
                User.is_active == True,
            )
        ) or 0

        if active_superadmins <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot deactivate the last active Superadmin",
            )

    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)

    return serialize_user_with_onboarding(user, bridge.get_department_map(), db=db)


@router.put(
    "/{user_id}/departments",
    response_model=UserResponse,
)
def update_teacher_departments(
    user_id: int,
    payload: TeacherDepartmentsUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    if current_user.role != Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin can assign departments to teachers",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    assigned_ids = validate_and_assign_teacher_departments(
        db=db,
        target_user=user,
        department_ids=payload.department_ids,
        assigned_by_user_id=current_user.id,
        bridge=bridge,
    )
    return serialize_user_with_onboarding(
        user,
        bridge.get_department_map(),
        assigned_dept_ids=assigned_ids,
    )
