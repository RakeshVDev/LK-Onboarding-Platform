"""SQLAlchemy Repository Implementations for Question Bank Ingestion & Live Classes."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.domain.training import (
    AssignableHostEntity,
    DepartmentEntity,
    LiveClassSessionEntity,
    ParsedQuestionCandidate,
)
from app.infrastructure.training.models import (
    AssessmentQuestionBank,
    AssessmentTemplate,
    Department,
    LiveClassSession,
    StudentDepartmentRequest,
)
from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
from services.identity.app.models.user import User as IdentityUser


def resolve_learner_exact_approved_department_id(db: Session, user_id: int) -> int | None:
    """Returns ONLY the learner's exact approved department ID after full onboarding unlock."""
    try:
        from services.training.app.routers import assessments as assessments_router

        flags = assessments_router._get_identity_onboarding_flags(user_id)
    except Exception:
        flags = None

    approved_req = db.scalar(
        select(StudentDepartmentRequest).where(
            StudentDepartmentRequest.user_id == user_id,
            StudentDepartmentRequest.status == "approved",
        )
    )

    if flags is not None and flags.get("role") == "learner":
        if not (
            flags.get("all_assessments_completed")
            and flags.get("is_activated_by_admin")
            and flags.get("department_approved")
        ):
            return None

        if approved_req is not None:
            return int(approved_req.department_id)

        raw_sel = flags.get("selected_department_id")
        if raw_sel is not None:
            try:
                return int(str(raw_sel).strip())
            except ValueError:
                return None
        return None

    if approved_req is not None:
        return int(approved_req.department_id)
    return None


class SqlAlchemyQuestionBankRepository:
    def __init__(self, db: Session):
        self.db = db

    def template_exists(self, template_id: int) -> bool:
        return self.db.get(AssessmentTemplate, template_id) is not None

    def get_template_type(self, template_id: int) -> str | None:
        tpl = self.db.get(AssessmentTemplate, template_id)
        return tpl.assessment_type if tpl is not None else None

    def bulk_insert(
        self,
        template_id: int,
        candidates: list[ParsedQuestionCandidate],
        created_by_user_id: int,
    ) -> list[int]:
        if not candidates:
            return []

        max_order = self.db.scalar(
            select(func.max(AssessmentQuestionBank.display_order)).where(
                AssessmentQuestionBank.template_id == template_id
            )
        )
        next_order = int(max_order or 0) + 1

        created_rows: list[AssessmentQuestionBank] = []
        for idx, item in enumerate(candidates):
            row = AssessmentQuestionBank(
                template_id=template_id,
                category=item.category,
                question_set=item.question_set,
                difficulty=item.difficulty,
                question_type=item.question_type,
                question_text=item.question_text,
                passage_text=item.passage_text,
                instructions=item.instructions,
                explanation=item.explanation,
                options=item.options,
                scoring_key=item.scoring_key or {},
                max_score=float(item.max_score),
                negative_marks=float(item.negative_marks),
                display_order=next_order + idx,
                in_assessment=True,
                is_active=True,
                created_by_user_id=created_by_user_id,
            )
            self.db.add(row)
            created_rows.append(row)

        self.db.flush()
        # Keep template question_count aligned when bank grows past configured count
        tpl = self.db.get(AssessmentTemplate, template_id)
        if tpl is not None and tpl.reading_passage is None:
            first_passage = next((c.passage_text for c in candidates if c.passage_text), None)
            if first_passage:
                tpl.reading_passage = first_passage

        self.db.commit()
        for row in created_rows:
            self.db.refresh(row)
        return [int(row.id) for row in created_rows]


class SqlAlchemyLiveClassRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_department(self, department_id: int) -> DepartmentEntity | None:
        dept = self.db.get(Department, department_id)
        if dept is None:
            return None
        return DepartmentEntity(
            id=int(dept.id),
            name=dept.name,
            description=dept.description,
            is_active=bool(dept.is_active),
        )

    def list_departments_map(self) -> dict[int, str]:
        rows = self.db.scalars(select(Department)).all()
        return {int(d.id): str(d.name) for d in rows}

    def _to_entity(self, row: LiveClassSession, dept_map: dict[int, str] | None = None) -> LiveClassSessionEntity:
        d_map = dept_map if dept_map is not None else self.list_departments_map()
        return LiveClassSessionEntity(
            id=int(row.id),
            title=row.title,
            description=row.description,
            department_id=int(row.department_id),
            department_name=d_map.get(int(row.department_id), "Department"),
            instructor_user_id=int(row.instructor_user_id),
            instructor_name=row.instructor_name,
            scheduled_start=row.scheduled_start,
            duration_minutes=int(row.duration_minutes),
            meeting_url=row.meeting_url,
            platform=row.platform,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create(self, session: LiveClassSessionEntity) -> LiveClassSessionEntity:
        row = LiveClassSession(
            title=session.title,
            description=session.description,
            department_id=session.department_id,
            instructor_user_id=session.instructor_user_id,
            instructor_name=session.instructor_name,
            scheduled_start=session.scheduled_start,
            duration_minutes=session.duration_minutes,
            meeting_url=session.meeting_url,
            platform=session.platform,
            status=session.status,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_entity(row)

    def get_by_id(self, session_id: int) -> LiveClassSessionEntity | None:
        row = self.db.get(LiveClassSession, session_id)
        return self._to_entity(row) if row is not None else None

    def list_sessions(self, department_id: int | None = None) -> list[LiveClassSessionEntity]:
        stmt = select(LiveClassSession).order_by(LiveClassSession.scheduled_start.asc(), LiveClassSession.id.desc())
        if department_id is not None:
            stmt = stmt.where(LiveClassSession.department_id == department_id)
        rows = self.db.scalars(stmt).all()
        dept_map = self.list_departments_map()
        return [self._to_entity(r, dept_map) for r in rows]

    def get_host_user(self, user_id: int) -> AssignableHostEntity | None:
        try:
            with IdentitySessionLocal() as id_db:
                user = id_db.get(IdentityUser, user_id)
                if user is None or not user.is_active:
                    return None
                raw_role = user.role.value if hasattr(user.role, "value") else user.role
                return AssignableHostEntity(
                    id=int(user.id),
                    full_name=str(user.full_name),
                    email=str(user.email),
                    role=str(raw_role).lower(),
                )
        except Exception as exc:
            logger.warning("Failed to fetch assignable host %s from Identity DB: %s", user_id, exc)
            return None

    def list_assignable_hosts(self, allowed_roles: tuple[str, ...]) -> list[AssignableHostEntity]:
        normalized = tuple(r.lower() for r in allowed_roles if r)
        if not normalized:
            return []
        try:
            with IdentitySessionLocal() as id_db:
                rows = id_db.scalars(
                    select(IdentityUser)
                    .where(
                        IdentityUser.is_active == True,  # noqa: E712 - T-SQL rejects `IS 1`
                        func.lower(IdentityUser.role).in_(normalized),
                    )
                    .order_by(IdentityUser.full_name.asc())
                ).all()
                return [
                    AssignableHostEntity(
                        id=int(u.id),
                        full_name=str(u.full_name),
                        email=str(u.email),
                        role=str(u.role.value if hasattr(u.role, "value") else u.role).lower(),
                    )
                    for u in rows
                ]
        except Exception as exc:
            logger.warning("Failed to list assignable hosts from Identity DB: %s", exc)
            return []

    def update(self, session: LiveClassSessionEntity) -> LiveClassSessionEntity:
        if session.id is None:
            raise ValueError("Cannot update unsaved LiveClassSession")
        row = self.db.get(LiveClassSession, session.id)
        if row is None:
            raise LookupError(f"LiveClassSession {session.id} not found")
        row.title = session.title
        row.description = session.description
        row.department_id = session.department_id
        row.instructor_user_id = session.instructor_user_id
        row.instructor_name = session.instructor_name
        row.scheduled_start = session.scheduled_start
        row.duration_minutes = session.duration_minutes
        row.meeting_url = session.meeting_url
        row.platform = session.platform
        row.status = session.status
        self.db.commit()
        self.db.refresh(row)
        return self._to_entity(row)

    def delete(self, session_id: int) -> bool:
        row = self.db.get(LiveClassSession, session_id)
        if row is None:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

