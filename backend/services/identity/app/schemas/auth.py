
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    all_assessments_completed: bool = False
    is_activated_by_admin: bool = False
    selected_department_id: str | None = None
    department_approved: bool = False
    selected_department_name: str | None = None
    assigned_department_ids: list[int] = Field(default_factory=list)
    assigned_department_names: list[str] = Field(default_factory=list)
    onboarding_stage: str | None = None
    results_cleared_at: datetime | None = None
    created_at: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
