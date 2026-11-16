"""SQLAlchemy repository implementation for Identity & Onboarding state."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.identity import Role, UserIdentity
from services.identity.app.models.user import User


def _to_domain(row: User) -> UserIdentity:
    role_val = str(row.role.value if hasattr(row.role, "value") else row.role).lower()
    return UserIdentity(
        id=int(row.id),
        full_name=row.full_name,
        email=row.email,
        role=Role(role_val),
        is_active=bool(row.is_active),
        all_assessments_completed=bool(getattr(row, "all_assessments_completed", False)),
        is_activated_by_admin=bool(getattr(row, "is_activated_by_admin", False)),
        selected_department_id=getattr(row, "selected_department_id", None),
        department_approved=bool(getattr(row, "department_approved", False)),
        created_at=getattr(row, "created_at", None),
    )


class SqlAlchemyIdentityUserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> UserIdentity | None:
        row = self.db.get(User, user_id)
        return _to_domain(row) if row is not None else None

    def save_onboarding_state(self, user: UserIdentity) -> UserIdentity:
        row = self.db.get(User, user.id)
        if row is None:
            raise LookupError(f"User {user.id} not found")
        row.all_assessments_completed = bool(user.all_assessments_completed)
        row.is_activated_by_admin = bool(user.is_activated_by_admin)
        row.selected_department_id = user.selected_department_id
        row.department_approved = bool(user.department_approved)
        self.db.commit()
        self.db.refresh(row)
        return _to_domain(row)

