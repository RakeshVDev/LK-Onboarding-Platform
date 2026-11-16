"""Department-Gated Live Classes & Video Sessions Use Cases."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from app.application.training.ports import LiveClassRepository
from app.domain.training import (
    AssignableHostEntity,
    LiveClassSessionEntity,
    LiveClassStatus,
)

STAFF_ROLES = {"superadmin", "admin", "teacher"}
ASSIGNABLE_ROLES_BY_ACTOR: dict[str, tuple[str, ...]] = {
    "superadmin": ("superadmin", "admin", "teacher"),
    "admin": ("admin", "teacher"),
    "teacher": ("teacher",),
}
ALLOWED_STATUSES = {s.value for s in LiveClassStatus}


class LiveClassAccessError(PermissionError):
    """Raised when an actor attempts to view, create, or join an unauthorized live session."""


class LiveClassValidationError(ValueError):
    """Raised when live class payload fails domain validation."""


def validate_meeting_url(raw_url: str) -> str:
    cleaned = (raw_url or "").strip()
    if not cleaned:
        raise LiveClassValidationError("Meeting / Video Call URL is required.")
    if cleaned.startswith("/live-room/"):
        return cleaned
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise LiveClassValidationError(
            "Meeting URL must be a valid http(s) link or internal /live-room/ path."
        )
    return cleaned


class LiveClassUseCase:
    """Enforces mandatory department binding and strict exact-department RBAC gating."""

    def __init__(self, repo: LiveClassRepository):
        self.repo = repo

    def list_assignable_hosts(
        self,
        *,
        actor_role: str,
        actor_user_id: int,
        actor_name: str | None = None,
        actor_email: str | None = None,
    ) -> list[AssignableHostEntity]:
        role_lower = (actor_role or "").lower()
        if role_lower not in STAFF_ROLES:
            raise LiveClassAccessError("Only teachers, admins, or superadmins can list live class instructors.")

        self_display = (actor_name or "").strip() or "Faculty Instructor"
        self_email = (actor_email or "").strip()
        allowed_roles = ASSIGNABLE_ROLES_BY_ACTOR[role_lower]
        hosts = list(self.repo.list_assignable_hosts(allowed_roles))
        if not any(h.id == actor_user_id for h in hosts):
            hosts.append(
                AssignableHostEntity(
                    id=actor_user_id,
                    full_name=self_display,
                    email=self_email,
                    role=role_lower,
                )
            )
        role_rank = {"superadmin": 0, "admin": 1, "teacher": 2}
        hosts.sort(key=lambda h: (role_rank.get(h.role.lower(), 9), h.full_name.lower()))
        return hosts

    def _resolve_target_instructor(
        self,
        *,
        actor_role: str,
        actor_user_id: int,
        actor_name: str | None,
        requested_instructor_user_id: int | None,
    ) -> tuple[int, str]:
        role_lower = (actor_role or "").lower()
        if role_lower not in STAFF_ROLES:
            raise LiveClassAccessError("Only teachers, admins, or superadmins can assign live class instructors.")

        self_display = (actor_name or "").strip() or "Faculty Instructor"
        if requested_instructor_user_id is None or requested_instructor_user_id == actor_user_id:
            return actor_user_id, self_display

        host = self.repo.get_host_user(requested_instructor_user_id)
        if host is None:
            raise LiveClassValidationError(
                "Selected instructor account was not found or is inactive."
            )
        host_role = (host.role or "").lower()
        if host_role not in STAFF_ROLES:
            raise LiveClassValidationError(
                "Selected live class instructor must be an active Teacher, Admin, or SuperAdmin."
            )

        allowed_roles = ASSIGNABLE_ROLES_BY_ACTOR[role_lower]
        if host_role not in allowed_roles:
            if role_lower == "teacher":
                raise LiveClassAccessError(
                    "Teachers can only assign another Teacher as the live class host, not an Admin or SuperAdmin."
                )
            raise LiveClassAccessError(
                "Admins can only assign a Teacher or Admin as the live class instructor, not a SuperAdmin."
            )
        return host.id, (host.full_name or "").strip() or "Faculty Instructor"

    def _ensure_teacher_department_scope(
        self,
        *,
        actor_role: str,
        department_id: int,
        teacher_allowed_department_ids: set[int] | None,
    ) -> None:
        if actor_role.lower() != "teacher":
            return
        if teacher_allowed_department_ids is None:
            return
        if not teacher_allowed_department_ids:
            raise LiveClassAccessError(
                "No departments have been assigned to your teacher account yet. Contact a SuperAdmin."
            )
        if int(department_id) not in teacher_allowed_department_ids:
            raise LiveClassAccessError(
                "Teachers can only schedule or manage live classes within their assigned departments."
            )

    def create_session(
        self,
        *,
        actor_role: str,
        actor_user_id: int,
        actor_name: str | None,
        title: str,
        description: str | None,
        department_id: int,
        scheduled_start: datetime,
        duration_minutes: int,
        meeting_url: str,
        platform: str = "Video Call",
        instructor_user_id: int | None = None,
        teacher_allowed_department_ids: set[int] | None = None,
    ) -> LiveClassSessionEntity:
        if actor_role.lower() not in STAFF_ROLES:
            raise LiveClassAccessError("Only teachers, admins, or superadmins can schedule live classes.")

        clean_title = (title or "").strip()
        if len(clean_title) < 3:
            raise LiveClassValidationError("Session title must be at least 3 characters long.")

        if duration_minutes <= 0 or duration_minutes > 480:
            raise LiveClassValidationError("Duration must be between 1 and 480 minutes.")

        dept = self.repo.get_department(department_id)
        if dept is None or not dept.is_active:
            raise LiveClassValidationError("A valid, active target Department must be selected.")
        if dept.name.strip().lower() in {"all / common", "all/common", "common"}:
            raise LiveClassValidationError("Live classes must be assigned to a specific department, not All / Common.")

        self._ensure_teacher_department_scope(
            actor_role=actor_role,
            department_id=department_id,
            teacher_allowed_department_ids=teacher_allowed_department_ids,
        )

        safe_url = validate_meeting_url(meeting_url)
        start_utc = (
            scheduled_start.replace(tzinfo=timezone.utc)
            if scheduled_start.tzinfo is None
            else scheduled_start.astimezone(timezone.utc)
        )
        target_instructor_id, target_instructor_name = self._resolve_target_instructor(
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            requested_instructor_user_id=instructor_user_id,
        )

        entity = LiveClassSessionEntity(
            id=None,
            title=clean_title,
            description=(description or "").strip() or None,
            department_id=dept.id,
            department_name=dept.name,
            instructor_user_id=target_instructor_id,
            instructor_name=target_instructor_name,
            scheduled_start=start_utc,
            duration_minutes=int(duration_minutes),
            meeting_url=safe_url,
            platform=(platform or "Video Call").strip() or "Video Call",
            status=LiveClassStatus.SCHEDULED.value,
        )
        return self.repo.create(entity)

    def list_sessions(
        self,
        *,
        actor_role: str,
        learner_approved_department_id: int | None,
        requested_department_id: int | None = None,
        teacher_allowed_department_ids: set[int] | None = None,
    ) -> list[LiveClassSessionEntity]:
        role = actor_role.lower()
        clean_req_dept_id = (
            int(requested_department_id)
            if isinstance(requested_department_id, (int, str)) and str(requested_department_id).isdigit()
            else None
        )
        if role == "teacher" and teacher_allowed_department_ids is not None:
            if not teacher_allowed_department_ids:
                return []
            if (
                clean_req_dept_id is not None
                and clean_req_dept_id not in teacher_allowed_department_ids
            ):
                return []
            return [
                s
                for s in self.repo.list_sessions(department_id=clean_req_dept_id)
                if s.department_id in teacher_allowed_department_ids
            ]

        if role in STAFF_ROLES:
            return self.repo.list_sessions(department_id=clean_req_dept_id)

        # Strict learner / employee exact-department gating:
        # Pending/unapproved candidates see zero sessions.
        if learner_approved_department_id is None:
            return []

        if requested_department_id is not None and requested_department_id != learner_approved_department_id:
            return []

        return [
            s
            for s in self.repo.list_sessions(department_id=learner_approved_department_id)
            if s.department_id == learner_approved_department_id and s.status != LiveClassStatus.CANCELLED.value
        ]

    def get_session_with_access_check(
        self,
        *,
        session_id: int,
        actor_role: str,
        learner_approved_department_id: int | None,
        teacher_allowed_department_ids: set[int] | None = None,
    ) -> LiveClassSessionEntity | None:
        session = self.repo.get_by_id(session_id)
        if session is None:
            return None

        if actor_role.lower() == "teacher" and teacher_allowed_department_ids is not None:
            self._ensure_teacher_department_scope(
                actor_role=actor_role,
                department_id=session.department_id,
                teacher_allowed_department_ids=teacher_allowed_department_ids,
            )
            return session

        if actor_role.lower() in STAFF_ROLES:
            return session

        if learner_approved_department_id is None:
            raise LiveClassAccessError(
                "You must complete onboarding and obtain department approval before viewing live sessions."
            )

        if session.department_id != learner_approved_department_id:
            raise LiveClassAccessError(
                "Access denied: this live session is restricted to another department."
            )

        if session.status == LiveClassStatus.CANCELLED.value:
            raise LiveClassAccessError("This live session has been cancelled.")

        return session

    def join_session(
        self,
        *,
        session_id: int,
        actor_role: str,
        learner_approved_department_id: int | None,
        teacher_allowed_department_ids: set[int] | None = None,
    ) -> LiveClassSessionEntity | None:
        session = self.get_session_with_access_check(
            session_id=session_id,
            actor_role=actor_role,
            learner_approved_department_id=learner_approved_department_id,
            teacher_allowed_department_ids=teacher_allowed_department_ids,
        )
        if session is None:
            return None
        if session.status != LiveClassStatus.LIVE.value:
            raise LiveClassValidationError(
                "This live class has not started yet. Join Live is only available once the assigned teacher starts the class."
            )
        return session

    def update_session(
        self,
        *,
        session_id: int,
        actor_role: str,
        actor_user_id: int,
        actor_name: str | None = None,
        instructor_user_id: int | None = None,
        title: str | None = None,
        description: str | None = None,
        department_id: int | None = None,
        scheduled_start: datetime | None = None,
        duration_minutes: int | None = None,
        meeting_url: str | None = None,
        platform: str | None = None,
        status: str | None = None,
        teacher_allowed_department_ids: set[int] | None = None,
    ) -> LiveClassSessionEntity | None:
        if actor_role.lower() not in STAFF_ROLES:
            raise LiveClassAccessError("Only teachers, admins, or superadmins can modify live classes.")

        existing = self.repo.get_by_id(session_id)
        if existing is None:
            return None

        self._ensure_teacher_department_scope(
            actor_role=actor_role,
            department_id=existing.department_id,
            teacher_allowed_department_ids=teacher_allowed_department_ids,
        )
        if department_id is not None:
            self._ensure_teacher_department_scope(
                actor_role=actor_role,
                department_id=department_id,
                teacher_allowed_department_ids=teacher_allowed_department_ids,
            )

        original_instructor_id = existing.instructor_user_id

        if instructor_user_id is not None and instructor_user_id != existing.instructor_user_id:
            target_id, target_name = self._resolve_target_instructor(
                actor_role=actor_role,
                actor_user_id=actor_user_id,
                actor_name=actor_name,
                requested_instructor_user_id=instructor_user_id,
            )
            existing.instructor_user_id = target_id
            existing.instructor_name = target_name

        if title is not None:
            clean_title = title.strip()
            if len(clean_title) < 3:
                raise LiveClassValidationError("Session title must be at least 3 characters long.")
            existing.title = clean_title

        if description is not None:
            existing.description = description.strip() or None

        if department_id is not None:
            dept = self.repo.get_department(department_id)
            if dept is None or not dept.is_active:
                raise LiveClassValidationError("Selected department does not exist or is inactive.")
            if dept.name.strip().lower() in {"all / common", "all/common", "common"}:
                raise LiveClassValidationError("Live classes must be assigned to a specific department, not All / Common.")
            existing.department_id = dept.id
            existing.department_name = dept.name

        if scheduled_start is not None:
            existing.scheduled_start = (
                scheduled_start.replace(tzinfo=timezone.utc)
                if scheduled_start.tzinfo is None
                else scheduled_start.astimezone(timezone.utc)
            )

        if duration_minutes is not None:
            if duration_minutes <= 0 or duration_minutes > 480:
                raise LiveClassValidationError("Duration must be between 1 and 480 minutes.")
            existing.duration_minutes = int(duration_minutes)

        if meeting_url is not None:
            existing.meeting_url = validate_meeting_url(meeting_url)

        if platform is not None:
            existing.platform = platform.strip() or "Video Call"

        if status is not None:
            clean_status = status.strip().lower()
            if clean_status not in ALLOWED_STATUSES:
                raise LiveClassValidationError(f"Unsupported live class status '{status}'.")
            if clean_status == LiveClassStatus.LIVE.value and actor_user_id != original_instructor_id:
                raise LiveClassAccessError(
                    "Only the selected teacher/instructor assigned to this session can start the live class."
                )
            if (
                clean_status == LiveClassStatus.COMPLETED.value
                and existing.status == LiveClassStatus.LIVE.value
                and actor_user_id != original_instructor_id
            ):
                raise LiveClassAccessError(
                    "Only the assigned teacher/instructor can end the live class."
                )
            existing.status = clean_status

        return self.repo.update(existing)

    def delete_session(
        self,
        *,
        session_id: int,
        actor_role: str,
        teacher_allowed_department_ids: set[int] | None = None,
    ) -> bool:
        if actor_role.lower() not in STAFF_ROLES:
            raise LiveClassAccessError("Only teachers, admins, or superadmins can delete live classes.")
        if actor_role.lower() == "teacher" and teacher_allowed_department_ids is not None:
            existing = self.repo.get_by_id(session_id)
            if existing is None:
                return False
            self._ensure_teacher_department_scope(
                actor_role=actor_role,
                department_id=existing.department_id,
                teacher_allowed_department_ids=teacher_allowed_department_ids,
            )
        return self.repo.delete(session_id)

