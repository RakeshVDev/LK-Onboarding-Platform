"""Shared 1:1 Department<->Course Vault sync, SuperAdmin consensus deletion, and batch cascade helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.infrastructure.training.models import LiveClassSession
from services.identity.app.core.roles import Role
from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
from services.identity.app.models.user import User, UserDepartment
from services.training.app.models.assessment import AssessmentTemplate
from services.training.app.models.cohort_workspace import (
    CohortAnnouncement,
    CohortAnnouncementRead,
    CohortAssignment,
    CohortAssignmentSubmission,
    CohortAttendanceEntry,
    CohortChapter,
    CohortDiscussion,
    CohortDiscussionLike,
    CohortDiscussionReply,
    CohortLesson,
    CohortQuiz,
    CohortQuizSubmission,
)
from services.training.app.models.entities import (
    AttendanceRecord,
    Cohort,
    CohortMaterialDelivery,
    CohortMember,
    CohortTeacher,
    Course,
    CourseEnrollment,
    Department,
    DepartmentCourseDeletionRequest,
    LearningMaterial,
    StudentDepartmentRequest,
    SyllabusItem,
    TimetableSession,
)
from services.training.app.services.teacher_scope import (
    COMMON_DEPARTMENT_NAMES,
    is_common_department_id,
)

MAX_TEACHER_DEPARTMENTS = 8
MAX_BATCH_TEACHERS = 3

COMMON_VAULT_DEFAULT_RESOURCES: tuple[tuple[str, str, str], ...] = (
    (
        "HTML — Semantics, Forms & Accessibility Reference",
        "link",
        "https://developer.mozilla.org/en-US/docs/Web/HTML",
    ),
    (
        "CSS — Flexbox, Grid & Modern Responsive Styling Guide",
        "link",
        "https://developer.mozilla.org/en-US/docs/Web/CSS",
    ),
    (
        "JS — JavaScript Core Concepts, Async/Await & DOM Mastery",
        "link",
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
    ),
    (
        "TS — TypeScript Handbook: Types, Interfaces & Generics",
        "link",
        "https://www.typescriptlang.org/docs/handbook/intro.html",
    ),
    (
        "Angular — Signals, Standalone Components & Routing Docs",
        "link",
        "https://angular.dev/overview",
    ),
    (
        "React — Components, Hooks & State Patterns Guide",
        "link",
        "https://react.dev/learn",
    ),
)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "materials"


def _is_common_name(name: str | None) -> bool:
    return (name or "").strip().lower() in COMMON_DEPARTMENT_NAMES


def ensure_course_for_department(
    db: Session,
    department: Department,
    *,
    seed_common_if_new: bool = True,
) -> Course:
    """Guarantee a single Course Vault exists for a Department (1:1 invariant)."""
    existing = db.scalars(
        select(Course).where(Course.department_id == department.id).order_by(Course.id.asc())
    ).first()
    created_now = False
    if existing is None:
        title = (
            "All / Common — Core Web & Engineering Resource Vault"
            if _is_common_name(department.name)
            else f"{department.name} — Course Resource Vault"
        )
        desc = department.description or f"Permanent resource vault and study materials for {department.name}."
        existing = Course(
            department_id=department.id,
            title=title[:200],
            description=desc,
            is_published=True,
        )
        db.add(existing)
        db.flush()
        created_now = True

    if seed_common_if_new and created_now and _is_common_name(department.name):
        has_any_material = db.scalars(
            select(LearningMaterial.id).where(LearningMaterial.course_id == existing.id)
        ).first()
        if has_any_material is None:
            for title, mat_type, url in COMMON_VAULT_DEFAULT_RESOURCES:
                db.add(
                    LearningMaterial(
                        course_id=existing.id,
                        title=title,
                        material_type=mat_type,
                        storage_key=url,
                        is_active=True,
                    )
                )
            db.flush()

    return existing


def ensure_department_courses_synced(
    db: Session,
    *,
    seed_common_if_empty: bool = False,
) -> dict[int, Course]:
    """Reconcile active departments so len(courses) == len(active departments), incl. All/Common."""
    departments = db.scalars(
        select(Department).where(Department.is_active == True).order_by(Department.id.asc())  # noqa: E712
    ).all()
    if not departments:
        return {}

    existing_courses = db.scalars(select(Course).order_by(Course.id.asc())).all()
    course_by_dept: dict[int, Course] = {}
    for c in existing_courses:
        course_by_dept.setdefault(int(c.department_id), c)

    dirty = False
    for dept in departments:
        had_course = int(dept.id) in course_by_dept
        course = course_by_dept.get(int(dept.id))
        if course is None:
            course = ensure_course_for_department(db, dept, seed_common_if_new=True)
            course_by_dept[int(dept.id)] = course
            dirty = True
        elif seed_common_if_empty and _is_common_name(dept.name):
            has_any = db.scalars(
                select(LearningMaterial.id).where(LearningMaterial.course_id == course.id)
            ).first()
            if has_any is None:
                for title, mat_type, url in COMMON_VAULT_DEFAULT_RESOURCES:
                    db.add(
                        LearningMaterial(
                            course_id=course.id,
                            title=title,
                            material_type=mat_type,
                            storage_key=url,
                            is_active=True,
                        )
                    )
                dirty = True

        # Ensure any cohorts under this department point to its 1:1 Course
        if had_course or course.id:
            unlinked = db.scalars(
                select(Cohort).where(
                    Cohort.department_id == dept.id,
                    Cohort.course_id.is_(None),
                )
            ).all()
            for cohort in unlinked:
                cohort.course_id = course.id
                dirty = True

    if dirty:
        db.commit()
        for course in course_by_dept.values():
            db.refresh(course)

    return course_by_dept


def get_active_superadmin_users(identity_session_factory=None) -> list[dict]:
    """Fetch all active SuperAdmin accounts from Identity DB."""
    session_cls = identity_session_factory or IdentitySessionLocal
    try:
        with session_cls() as id_db:
            rows = id_db.scalars(
                select(User)
                .where(
                    User.role == Role.SUPERADMIN.value,
                    User.is_active == True,  # noqa: E712
                )
                .order_by(User.id.asc())
            ).all()
            return [
                {
                    "id": int(u.id),
                    "full_name": u.full_name,
                    "email": u.email,
                }
                for u in rows
            ]
    except Exception:
        return []


def ensure_teacher_has_department(
    db: Session,
    teacher_id: int,
    department_id: int,
    assigned_by_user_id: int | None,
    *,
    max_depts: int = MAX_TEACHER_DEPARTMENTS,
    identity_session_factory=None,
) -> None:
    """Ensure a teacher is assigned to department_id, respecting the 8-department cap."""
    if is_common_department_id(db, department_id):
        return

    active_concrete_dept_ids = {
        int(d.id)
        for d in db.scalars(select(Department).where(Department.is_active == True)).all()  # noqa: E712
        if not _is_common_name(d.name)
    }
    if int(department_id) not in active_concrete_dept_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target active department not found",
        )

    session_cls = identity_session_factory or IdentitySessionLocal
    with session_cls() as id_db:
        teacher = id_db.get(User, int(teacher_id))
        if teacher is None or not teacher.is_active or str(teacher.role).lower() != Role.TEACHER.value:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"User ID {teacher_id} is not an active Teacher account.",
            )

        existing_rows = id_db.scalars(
            select(UserDepartment).where(UserDepartment.user_id == int(teacher_id))
        ).all()
        existing_concrete = {
            int(r.department_id)
            for r in existing_rows
            if int(r.department_id) in active_concrete_dept_ids
        }
        if int(department_id) in existing_concrete:
            return

        if len(existing_concrete) >= max_depts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Teacher '{teacher.full_name}' already has {len(existing_concrete)} departments "
                    f"(maximum is {max_depts}). Remove one before assigning this batch."
                ),
            )

        id_db.add(
            UserDepartment(
                user_id=int(teacher_id),
                department_id=int(department_id),
                assigned_by_user_id=assigned_by_user_id,
            )
        )
        id_db.commit()


def remove_department_from_identity_users(
    department_id: int,
    *,
    identity_session_factory=None,
) -> None:
    """Clean up Identity UserDepartment rows and stale selected_department_id references."""
    session_cls = identity_session_factory or IdentitySessionLocal
    try:
        with session_cls() as id_db:
            id_db.execute(
                delete(UserDepartment).where(UserDepartment.department_id == int(department_id))
            )
            stale_learners = id_db.scalars(
                select(User).where(User.selected_department_id == str(int(department_id)))
            ).all()
            for u in stale_learners:
                u.selected_department_id = None
                u.department_approved = False
            id_db.commit()
    except Exception:
        pass


def _purge_workspace_for_scope(
    db: Session,
    *,
    cohort_ids: list[int] | None = None,
    department_id: int | None = None,
) -> None:
    """Cleanly remove cohort workspace rows scoped to deleted cohorts or a deleted department."""
    filters = []
    if cohort_ids:
        filters.append(("cohort_id", cohort_ids))
    if department_id is not None:
        filters.append(("department_id", int(department_id)))
    if not filters:
        return

    def _scope_clause(model):
        from sqlalchemy import or_
        clauses = []
        if cohort_ids:
            clauses.append(model.cohort_id.in_(cohort_ids))
        if department_id is not None and hasattr(model, "department_id"):
            clauses.append(model.department_id == int(department_id))
        return or_(*clauses)

    chapter_ids = list(db.scalars(select(CohortChapter.id).where(_scope_clause(CohortChapter))).all())
    if chapter_ids:
        db.execute(delete(CohortLesson).where(CohortLesson.chapter_id.in_(chapter_ids)))
    lesson_clause = _scope_clause(CohortLesson)
    db.execute(delete(CohortLesson).where(lesson_clause))
    db.execute(delete(CohortChapter).where(_scope_clause(CohortChapter)))

    assignment_ids = list(db.scalars(select(CohortAssignment.id).where(_scope_clause(CohortAssignment))).all())
    if assignment_ids:
        db.execute(delete(CohortAssignmentSubmission).where(CohortAssignmentSubmission.assignment_id.in_(assignment_ids)))
        db.execute(delete(CohortAssignment).where(CohortAssignment.id.in_(assignment_ids)))

    quiz_ids = list(db.scalars(select(CohortQuiz.id).where(_scope_clause(CohortQuiz))).all())
    if quiz_ids:
        db.execute(delete(CohortQuizSubmission).where(CohortQuizSubmission.quiz_id.in_(quiz_ids)))
        db.execute(delete(CohortQuiz).where(CohortQuiz.id.in_(quiz_ids)))

    ann_ids = list(db.scalars(select(CohortAnnouncement.id).where(_scope_clause(CohortAnnouncement))).all())
    if ann_ids:
        db.execute(delete(CohortAnnouncementRead).where(CohortAnnouncementRead.announcement_id.in_(ann_ids)))
        db.execute(delete(CohortAnnouncement).where(CohortAnnouncement.id.in_(ann_ids)))

    disc_ids = list(db.scalars(select(CohortDiscussion.id).where(_scope_clause(CohortDiscussion))).all())
    if disc_ids:
        db.execute(delete(CohortDiscussionLike).where(CohortDiscussionLike.discussion_id.in_(disc_ids)))
        db.execute(delete(CohortDiscussionReply).where(CohortDiscussionReply.discussion_id.in_(disc_ids)))
        db.execute(delete(CohortDiscussion).where(CohortDiscussion.id.in_(disc_ids)))

    if cohort_ids:
        db.execute(delete(CohortAttendanceEntry).where(CohortAttendanceEntry.cohort_id.in_(cohort_ids)))


def purge_cohort_records(
    db: Session,
    cohort_id: int,
    *,
    delete_cohort_row: bool = True,
) -> Cohort:
    """Purge all batch-level cohort deliveries, memberships, teacher links, schedules, and workspace items."""
    cohort = db.get(Cohort, cohort_id)
    if cohort is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cohort / Batch not found",
        )

    db.execute(
        delete(CohortMaterialDelivery).where(CohortMaterialDelivery.cohort_id == cohort_id)
    )
    db.execute(delete(CohortTeacher).where(CohortTeacher.cohort_id == cohort_id))
    db.execute(delete(CohortMember).where(CohortMember.cohort_id == cohort_id))
    _purge_workspace_for_scope(db, cohort_ids=[cohort_id])

    session_ids = list(
        db.scalars(select(TimetableSession.id).where(TimetableSession.cohort_id == cohort_id)).all()
    )
    if session_ids:
        db.execute(delete(AttendanceRecord).where(AttendanceRecord.session_id.in_(session_ids)))
        db.execute(delete(TimetableSession).where(TimetableSession.id.in_(session_ids)))

    if delete_cohort_row:
        db.delete(cohort)
    else:
        cohort.status = "completed"

    db.commit()
    return cohort


def _remove_stored_file_quietly(storage_key: str | None) -> None:
    if not storage_key or "://" in storage_key:
        return
    try:
        candidate = (UPLOAD_DIR / storage_key).resolve()
        if candidate.is_relative_to(UPLOAD_DIR.resolve()) and candidate.is_file():
            candidate.unlink()
    except Exception:
        pass


def execute_department_and_course_cascade_delete(
    db: Session,
    department_id: int,
    *,
    identity_session_factory=None,
) -> dict:
    """Delete both a Department and its paired Course (+ dependent cohorts/materials) cleanly."""
    dept = db.get(Department, department_id)
    if dept is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    course_ids = list(
        db.scalars(select(Course.id).where(Course.department_id == department_id)).all()
    )
    cohort_ids = list(
        db.scalars(select(Cohort.id).where(Cohort.department_id == department_id)).all()
    )

    if cohort_ids:
        db.execute(
            delete(CohortMaterialDelivery).where(CohortMaterialDelivery.cohort_id.in_(cohort_ids))
        )
        db.execute(delete(CohortTeacher).where(CohortTeacher.cohort_id.in_(cohort_ids)))
        db.execute(delete(CohortMember).where(CohortMember.cohort_id.in_(cohort_ids)))
        session_ids = list(
            db.scalars(
                select(TimetableSession.id).where(TimetableSession.cohort_id.in_(cohort_ids))
            ).all()
        )
        if session_ids:
            db.execute(delete(AttendanceRecord).where(AttendanceRecord.session_id.in_(session_ids)))
            db.execute(delete(TimetableSession).where(TimetableSession.id.in_(session_ids)))
        db.execute(delete(Cohort).where(Cohort.id.in_(cohort_ids)))

    _purge_workspace_for_scope(db, cohort_ids=cohort_ids or None, department_id=department_id)

    if course_ids:
        db.execute(
            delete(CohortMaterialDelivery).where(CohortMaterialDelivery.course_id.in_(course_ids))
        )
        materials = db.scalars(
            select(LearningMaterial).where(LearningMaterial.course_id.in_(course_ids))
        ).all()
        for mat in materials:
            _remove_stored_file_quietly(mat.storage_key)
        db.execute(delete(LearningMaterial).where(LearningMaterial.course_id.in_(course_ids)))
        db.execute(delete(SyllabusItem).where(SyllabusItem.course_id.in_(course_ids)))
        db.execute(delete(CourseEnrollment).where(CourseEnrollment.course_id.in_(course_ids)))
        db.execute(delete(Course).where(Course.id.in_(course_ids)))

    db.execute(delete(LiveClassSession).where(LiveClassSession.department_id == department_id))
    db.execute(
        delete(StudentDepartmentRequest).where(
            StudentDepartmentRequest.department_id == department_id
        )
    )

    # Preserve completed AssessmentSession snapshots while detaching AssessmentTemplate FK
    templates = db.scalars(
        select(AssessmentTemplate).where(AssessmentTemplate.department_id == department_id)
    ).all()
    for tpl in templates:
        tpl.department_id = None
        tpl.is_active = False

    dept_name = dept.name
    db.delete(dept)
    db.commit()

    remove_department_from_identity_users(
        department_id,
        identity_session_factory=identity_session_factory,
    )

    return {
        "department_id": department_id,
        "department_name": dept_name,
        "deleted_course_ids": course_ids,
        "deleted_cohort_ids": cohort_ids,
    }


def _parse_int_list(raw_json: str | None) -> list[int]:
    if not raw_json:
        return []
    try:
        loaded = json.loads(raw_json)
        if isinstance(loaded, list):
            seen: list[int] = []
            for item in loaded:
                val = int(item)
                if val not in seen:
                    seen.append(val)
            return seen
    except Exception:
        pass
    return []


def serialize_deletion_request(
    req: DepartmentCourseDeletionRequest,
    superadmins: list[dict],
) -> dict:
    approved_ids = _parse_int_list(req.approved_by_user_ids_json)
    sa_by_id = {int(sa["id"]): sa["full_name"] for sa in superadmins}
    required_ids = [int(sa["id"]) for sa in superadmins] or [int(req.initiated_by_user_id)]
    approved_names = [sa_by_id.get(uid, f"SuperAdmin #{uid}") for uid in approved_ids]
    pending_names = [
        sa_by_id.get(uid, f"SuperAdmin #{uid}")
        for uid in required_ids
        if uid not in approved_ids
    ]

    return {
        "id": req.id,
        "department_id": req.department_id,
        "department_name": req.department_name,
        "course_id": req.course_id,
        "target_type": req.target_type,
        "initiated_by_user_id": req.initiated_by_user_id,
        "initiated_by_name": sa_by_id.get(
            int(req.initiated_by_user_id), f"SuperAdmin #{req.initiated_by_user_id}"
        ),
        "approved_by_user_ids": approved_ids,
        "approved_by_names": approved_names,
        "required_superadmin_ids": required_ids,
        "pending_superadmin_names": pending_names,
        "approved_count": len([uid for uid in approved_ids if uid in set(required_ids)]),
        "required_count": len(required_ids),
        "status": req.status,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
    }


def initiate_or_approve_deletion(
    db: Session,
    *,
    department: Department,
    target_type: str,
    course_id: int | None,
    current_user_id: int,
    identity_session_factory=None,
) -> tuple[bool, dict]:
    """Create or advance unanimous active-SuperAdmin deletion approval for dept+course."""
    superadmins = get_active_superadmin_users(identity_session_factory=identity_session_factory)
    required_ids = {int(sa["id"]) for sa in superadmins}
    if not required_ids:
        required_ids = {int(current_user_id)}

    pending_req = db.scalars(
        select(DepartmentCourseDeletionRequest)
        .where(
            DepartmentCourseDeletionRequest.department_id == department.id,
            DepartmentCourseDeletionRequest.status == "pending",
        )
        .order_by(DepartmentCourseDeletionRequest.id.desc())
    ).first()

    if pending_req is None:
        approved_ids = [int(current_user_id)]
        pending_req = DepartmentCourseDeletionRequest(
            department_id=department.id,
            department_name=department.name,
            course_id=course_id,
            target_type=target_type,
            initiated_by_user_id=int(current_user_id),
            approved_by_user_ids_json=json.dumps(approved_ids),
            status="pending",
        )
        db.add(pending_req)
        db.flush()
    else:
        approved_ids = _parse_int_list(pending_req.approved_by_user_ids_json)
        if int(current_user_id) not in approved_ids:
            approved_ids.append(int(current_user_id))
            pending_req.approved_by_user_ids_json = json.dumps(approved_ids)

    is_unanimous = required_ids.issubset(set(approved_ids))
    if is_unanimous:
        pending_req.status = "executed"
        db.commit()
        db.refresh(pending_req)
        payload = serialize_deletion_request(pending_req, superadmins)
        execute_department_and_course_cascade_delete(
            db,
            department.id,
            identity_session_factory=identity_session_factory,
        )
        return True, payload

    db.commit()
    db.refresh(pending_req)
    return False, serialize_deletion_request(pending_req, superadmins)
