"""Pure application orchestrator for Strict Sequential Onboarding & Navigation Permissions."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.identity import NavPermission, OnboardingStage, Role, UserIdentity


RESTRICTED_LEARNER_NAV: tuple[NavPermission, ...] = (
    NavPermission(key="assessment", label="Assessment", route="/my-assessments", allowed=True),
    NavPermission(key="result", label="Result", route="/my-results", allowed=True),
    NavPermission(key="report", label="Report", route="/my-reports", allowed=True),
)

FULL_LEARNER_NAV: tuple[NavPermission, ...] = (
    NavPermission(key="dashboard", label="Dashboard", route="/dashboard", allowed=True),
    NavPermission(key="courses", label="Courses", route="/courses", allowed=True),
    NavPermission(key="cohorts", label="Cohorts", route="/cohorts", allowed=True),
    NavPermission(key="live_classes", label="Live Classes", route="/live-classes", allowed=True),
    NavPermission(key="assessment", label="Assessment", route="/my-assessments", allowed=True),
    NavPermission(key="result", label="Result", route="/my-results", allowed=True),
    NavPermission(key="report", label="Report", route="/my-reports", allowed=True),
    NavPermission(key="profile", label="Profile", route="/profile", allowed=True),
)


@dataclass(frozen=True, slots=True)
class NavigationPermissionsResult:
    stage: OnboardingStage
    is_assessment_only_mode: bool
    allowed_nav_keys: tuple[str, ...]
    nav_items: tuple[NavPermission, ...]


class OnboardingWorkflowUseCase:
    """Computes strict sidebar navigation gates based on user onboarding stage."""

    def resolve_navigation(self, user: UserIdentity) -> NavigationPermissionsResult:
        stage = user.onboarding_stage()
        if user.role != Role.LEARNER:
            keys = ["dashboard", "courses", "cohorts", "live_classes", "assessments", "assessment_results", "profile"]
            if user.role in {Role.SUPERADMIN, Role.ADMIN, Role.TEACHER}:
                keys.append("departments")
            if user.role in {Role.SUPERADMIN, Role.ADMIN}:
                keys.append("users")
            items = tuple(
                NavPermission(key=k, label=k.replace("_", " ").title(), route=f"/{k.replace('_', '-')}")
                for k in keys
            )
            return NavigationPermissionsResult(
                stage=OnboardingStage.FULLY_UNLOCKED,
                is_assessment_only_mode=False,
                allowed_nav_keys=tuple(keys),
                nav_items=items,
            )

        if stage == OnboardingStage.FULLY_UNLOCKED:
            return NavigationPermissionsResult(
                stage=stage,
                is_assessment_only_mode=False,
                allowed_nav_keys=tuple(i.key for i in FULL_LEARNER_NAV),
                nav_items=FULL_LEARNER_NAV,
            )

        items = list(RESTRICTED_LEARNER_NAV)
        if stage in {
            OnboardingStage.DEPARTMENT_SELECTION_REQUIRED,
            OnboardingStage.PENDING_DEPARTMENT_APPROVAL,
        }:
            items.append(
                NavPermission(
                    key="department_selection",
                    label="Department Selection",
                    route="/department-selection",
                    allowed=True,
                )
            )
        return NavigationPermissionsResult(
            stage=stage,
            is_assessment_only_mode=True,
            allowed_nav_keys=tuple(i.key for i in items),
            nav_items=tuple(items),
        )

