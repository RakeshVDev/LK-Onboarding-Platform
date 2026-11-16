
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.identity.app.core.security import (
    create_access_token,
    verify_password,
)
from services.identity.app.dependencies.auth import get_current_user, get_db
from services.identity.app.models.user import User
from services.identity.app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserProfileUpdateRequest,
    UserResponse,
)
from services.identity.app.services.onboarding import (
    TrainingOnboardingBridge,
    get_training_bridge,
    serialize_user_with_onboarding,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    return serialize_user_with_onboarding(
        current_user,
        bridge.get_department_map(),
        db=db,
    )


@router.put("/profile", response_model=UserResponse)
def update_profile(
    payload: UserProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    bridge: TrainingOnboardingBridge = Depends(get_training_bridge),
):
    current_user.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(current_user)
    return serialize_user_with_onboarding(
        current_user,
        bridge.get_department_map(),
        db=db,
    )


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}
