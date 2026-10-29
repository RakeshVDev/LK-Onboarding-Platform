
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.identity.app.core.roles import Role
from services.identity.app.dependencies.auth import (
    get_current_user,
    get_db,
    require_roles,
)
from services.identity.app.models.user import User
from services.identity.app.schemas.roles import (
    RoleUpdateRequest,
    RoleUpdateResponse,
)

router = APIRouter(
    prefix="/api/v1/users",
    tags=["Role Management"],
)


@router.patch(
    "/{user_id}/role",
    response_model=RoleUpdateResponse,
)
def update_user_role(
    user_id: int,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(Role.SUPERADMIN)
    ),
):
    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Do not allow removal of the final superadmin.
    if (
        user.role == Role.SUPERADMIN.value
        and payload.role != Role.SUPERADMIN
    ):
        superadmin_count = db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role == Role.SUPERADMIN.value,
                User.is_active.is_(True),
            )
        ) or 0

        if user.is_active and superadmin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last active superadmin",
            )

    user.role = payload.role.value
    db.commit()
    db.refresh(user)

    return user
