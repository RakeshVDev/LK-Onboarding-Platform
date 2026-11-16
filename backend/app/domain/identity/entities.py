"""Pure domain entities and value objects for Identity & Sequential Onboarding."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Role(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    TEACHER = "teacher"
    LEARNER = "learner"


class OnboardingStage(str, Enum):
    ASSESSMENT_PENDING = "assessment_pending"
    PENDING_ADMIN_ACTIVATION = "pending_admin_activation"
    DEPARTMENT_SELECTION_REQUIRED = "department_selection_required"
    PENDING_DEPARTMENT_APPROVAL = "pending_department_approval"
    FULLY_UNLOCKED = "fully_unlocked"


@dataclass(frozen=True, slots=True)
class NavPermission:
    key: str
    label: str
    route: str
    allowed: bool = True


@dataclass(slots=True)
class UserIdentity:
    id: int
    full_name: str
    email: str
    role: Role
    is_active: bool = True
    all_assessments_completed: bool = False
    is_activated_by_admin: bool = False
    selected_department_id: str | None = None
    department_approved: bool = False
    created_at: datetime | None = None

    def onboarding_stage(self) -> OnboardingStage:
        if self.role != Role.LEARNER:
            return OnboardingStage.FULLY_UNLOCKED
        if not self.all_assessments_completed:
            return OnboardingStage.ASSESSMENT_PENDING
        if not self.is_activated_by_admin:
            return OnboardingStage.PENDING_ADMIN_ACTIVATION
        if not self.selected_department_id:
            return OnboardingStage.DEPARTMENT_SELECTION_REQUIRED
        if not self.department_approved:
            return OnboardingStage.PENDING_DEPARTMENT_APPROVAL
        return OnboardingStage.FULLY_UNLOCKED

    def is_assessment_only_mode(self) -> bool:
        return self.onboarding_stage() != OnboardingStage.FULLY_UNLOCKED


@dataclass(slots=True)
class DepartmentSelectionRecord:
    user_id: int
    department_id: int
    status: str = "pending"
    notes: str | None = None
    reviewed_by_user_id: int | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)

