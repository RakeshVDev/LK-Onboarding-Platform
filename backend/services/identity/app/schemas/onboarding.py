from pydantic import BaseModel, ConfigDict, Field, field_validator

from services.identity.app.schemas.auth import UserResponse


class NavItemPermission(BaseModel):
    key: str
    label: str
    route: str
    allowed: bool = True


class NavigationPermissionsResponse(BaseModel):
    role: str
    onboarding_stage: str
    all_assessments_completed: bool
    is_activated_by_admin: bool
    selected_department_id: str | None = None
    selected_department_name: str | None = None
    department_approved: bool
    is_unlocked: bool
    assessment_only_mode: bool
    can_select_department: bool
    redirect_to: str
    allowed_items: list[str]
    locked_items: list[str]
    nav_items: list[NavItemPermission]
    status_message: str


class SelectDepartmentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    department_id: str | int
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("department_id")
    @classmethod
    def validate_department_id(cls, value: str | int) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("department_id cannot be empty")
        return normalized


class ApproveDepartmentRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    department_id: str | int | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("department_id")
    @classmethod
    def validate_department_id(cls, value: str | int | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        if not normalized:
            raise ValueError("department_id cannot be empty")
        return normalized


class AssessmentCompletionResponse(BaseModel):
    user: UserResponse
    permissions: NavigationPermissionsResponse
    total_assigned: int = 0
    completed_count: int = 0
    pending_count: int = 0
    message: str

