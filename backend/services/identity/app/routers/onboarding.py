from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from services.identity.app.core.roles import Role
from services.identity.app.dependencies.auth import get_current_user, get_db
from services.identity.app.models.user import User
from services.identity.app.schemas.auth import UserResponse
from services.identity.app.schemas.onboarding import (
    ApproveDepartmentRequest,
    AssessmentCompletionResponse,
    NavigationPermissionsResponse,
    SelectDepartmentRequest,
)
from services.identity.app.services.onboarding import (
    TrainingOnboardingBridge,
    build_navigation_permissions,
    get_training_bridge,
    serialize_user_with_onboarding,
    sync_learner_assessments_if_completed,
    validate_selectable_department,
)

router = APIRouter(prefix="/api", tags=["Onboarding & Navigation"])


def _ensure_admin(current_user: User) -> None:
    if current_user.role not in {Role.SUPERADMIN.value, Role.ADMIN.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Superadmin users can perform this action",
        )


def _resolve_department_name(
    user: User,
    bridge: TrainingOnboardingBridge,
) -> str | None:
    if not user.selected_department_id:
        return None
    dept_map = bridge.get_department_map()
    if str(user.selected_department_id) in dept_map:
        return dept_map[str(user.selected_department_id)]
    dept = bridge.get_department_by_id(user.selected_department_id)
    return str(dept["name"]) if dept else None


@router.get("/navigation/permissions", response_model=NavigationPermissionsResponse)
def get_navigation_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    sync_learner_assessments_if_completed(db, current_user, bridge)
    dept_name = _resolve_department_name(current_user, bridge)
    return build_navigation_permissions(current_user, department_name=dept_name)


@router.post("/assessments/complete", response_model=AssessmentCompletionResponse)
def complete_onboarding_assessments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    if current_user.role != Role.LEARNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only learners submit onboarding assessment completion",
        )

    try:
        status_info = bridge.get_assessment_status(current_user.id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify assessment completion right now",
        ) from exc

    total_assigned = int(status_info.get("total_assigned", 0))
    completed_count = int(status_info.get("completed_count", 0))
    pending_count = int(status_info.get("pending_count", 0))
    all_done = bool(status_info.get("all_completed", False)) and (
        total_assigned > 0 or bool(status_info.get("pre_assessments_completed", False))
    )

    if not all_done and not bool(current_user.all_assessments_completed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You must complete all assigned assessments before finalizing this step",
        )

    if not bool(current_user.all_assessments_completed):
        current_user.all_assessments_completed = True
        db.commit()
        db.refresh(current_user)

    dept_name = _resolve_department_name(current_user, bridge)
    permissions = build_navigation_permissions(current_user, department_name=dept_name)
    user_payload = serialize_user_with_onboarding(
        current_user,
        {str(current_user.selected_department_id): dept_name} if dept_name and current_user.selected_department_id else {},
    )
    return AssessmentCompletionResponse(
        user=user_payload,
        permissions=permissions,
        total_assigned=total_assigned,
        completed_count=completed_count,
        pending_count=pending_count,
        message="All onboarding assessments recorded as completed.",
    )


@router.post("/admin/users/{user_id}/activate", response_model=UserResponse)
def admin_activate_user_onboarding(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    _ensure_admin(current_user)

    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if (
        current_user.role == Role.ADMIN.value
        and target.role != Role.LEARNER.value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins can activate Learner onboarding accounts only",
        )

    if target.role != Role.LEARNER.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only learner accounts undergo sequential onboarding activation",
        )

    if not target.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User login account is disabled. Enable login before activating onboarding.",
        )

    sync_learner_assessments_if_completed(db, target, bridge)
    if not bool(target.all_assessments_completed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has not completed all assigned assessments yet",
        )

    if not bool(target.is_activated_by_admin):
        target.is_activated_by_admin = True
        db.commit()
        db.refresh(target)

    dept_map = bridge.get_department_map()
    return serialize_user_with_onboarding(target, dept_map)


@router.post("/users/me/select-department", response_model=UserResponse)
def select_my_department(
    payload: SelectDepartmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    if current_user.role != Role.LEARNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only learners select a specialization department",
        )

    sync_learner_assessments_if_completed(db, current_user, bridge)
    if not bool(current_user.all_assessments_completed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Complete all assigned assessments before selecting a department",
        )

    if not bool(current_user.is_activated_by_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Department selection unlocks only after an administrator activates your account",
        )

    if bool(current_user.department_approved):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your department selection is already approved and locked",
        )

    dept = validate_selectable_department(bridge, payload.department_id)
    bridge.upsert_department_request(
        user_id=current_user.id,
        department_id=int(dept["id"]),
        notes=payload.notes,
    )

    current_user.selected_department_id = str(dept["id"])
    db.commit()
    db.refresh(current_user)

    return serialize_user_with_onboarding(
        current_user,
        {str(dept["id"]): str(dept["name"])},
    )


@router.post("/admin/users/{user_id}/approve-department", response_model=UserResponse)
def admin_approve_user_department(
    user_id: int,
    payload: ApproveDepartmentRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    _ensure_admin(current_user)

    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if (
        current_user.role == Role.ADMIN.value
        and target.role != Role.LEARNER.value
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins can approve Learner department selections only",
        )

    if target.role != Role.LEARNER.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only learner accounts undergo department approval",
        )

    if not bool(target.all_assessments_completed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has not completed all assigned assessments yet",
        )

    if not bool(target.is_activated_by_admin):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User must be activated by an administrator before department approval",
        )

    chosen_dept_id = (
        payload.department_id
        if payload and payload.department_id is not None
        else target.selected_department_id
    )
    if not chosen_dept_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has not submitted a department choice yet",
        )

    dept = validate_selectable_department(bridge, chosen_dept_id)
    bridge.approve_department_request(
        user_id=target.id,
        department_id=int(dept["id"]),
        reviewer_id=current_user.id,
        notes=payload.notes if payload else None,
    )

    target.selected_department_id = str(dept["id"])
    target.department_approved = True
    db.commit()
    db.refresh(target)

    return serialize_user_with_onboarding(
        target,
        {str(dept["id"]): str(dept["name"])},
    )

