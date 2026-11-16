"""Application ports (interfaces) for Identity & Onboarding use cases."""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.identity import OnboardingStage, UserIdentity


class IdentityUserRepository(Protocol):
    def get_by_id(self, user_id: int) -> UserIdentity | None:
        ...

    def save_onboarding_state(self, user: UserIdentity) -> UserIdentity:
        ...


class TrainingSyncPort(Protocol):
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

    def get_approved_department_id(self, user_id: int) -> int | None:
        ...


def stage_from_user(user: UserIdentity) -> OnboardingStage:
    return user.onboarding_stage()

