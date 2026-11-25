"""Persistent SQL-backed API endpoints for Cohort Workspace features (replacing browser localStorage)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
from typing import Any
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.identity.app.core.roles import Role
from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
from services.identity.app.dependencies.auth import get_current_user
from services.identity.app.models.user import User as IdentityUser
from services.training.app.db.session import SessionLocal
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
    CohortMaterialBookmark,
    CohortQuiz,
    CohortQuizSubmission,
)
from services.training.app.models.entities import (
    Cohort,
    CohortMaterialDelivery,
    CohortMember,
    CohortTeacher,
    Course,
    Department,
    LearningMaterial,
)
from services.training.app.routers.assessments import get_learner_allowed_dept_ids
from services.training.app.schemas.cohort_workspace import (
    AnnouncementCreateRequest,
    AssignmentCreateRequest,
    AssignmentGradeRequest,
    AssignmentSubmitRequest,
    AttendanceBulkRequest,
    AttendanceCheckInRequest,
    AttendanceToggleRequest,
    BookmarkToggleRequest,
    ChapterCreateRequest,
    DiscussionCreateRequest,
    DiscussionReplyCreateRequest,
    LessonCreateRequest,
    QuizCreateRequest,
    QuizSubmitRequest,
    WorkspaceResponse,
)
from services.training.app.services.teacher_scope import (
    get_common_department_ids,
    require_teacher_department_access,
    resolve_teacher_scope,
    role_str,
)

router = APIRouter(prefix="/cohorts/workspace", tags=["Cohort Workspace"])

_STAFF_ROLES = {Role.SUPERADMIN.value, Role.ADMIN.value, Role.TEACHER.value}

ASSIGNMENT_SUBMISSIONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "assignment_submissions")
)
ASSIGNMENT_ATTACHMENTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "assignment_attachments")
)
COHORT_DOWNLOADABLES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "cohort_downloadables")
)
for _upload_dir in (ASSIGNMENT_SUBMISSIONS_DIR, ASSIGNMENT_ATTACHMENTS_DIR, COHORT_DOWNLOADABLES_DIR):
    os.makedirs(_upload_dir, exist_ok=True)

ALLOWED_SUBMISSION_EXTENSIONS = {
    ".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".pdf", ".docx", ".doc",
    ".pptx", ".ppt", ".xlsx", ".xls", ".csv", ".txt", ".md", ".json",
    ".sql", ".py", ".js", ".ts", ".java", ".cs", ".php",
}
ALLOWED_RESOURCE_EXTENSIONS = ALLOWED_SUBMISSION_EXTENSIONS | {".html", ".css", ".png", ".jpg", ".jpeg"}
MAX_SUBMISSION_BYTES = 25 * 1024 * 1024


def _format_byte_size(num_bytes: int) -> str:
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.1f} MB"


async def _save_uploaded_file(
    upload: UploadFile,
    target_dir: str,
    prefix: str,
    allowed_exts: set[str],
) -> tuple[str, str, str]:
    raw_name = os.path.basename((upload.filename or "").strip())
    if not raw_name:
        raise HTTPException(status_code=422, detail="Uploaded file must have a valid filename.")
    _, ext = os.path.splitext(raw_name)
    ext_lower = ext.lower()
    if ext_lower not in allowed_exts:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext_lower}'. Allowed types: PDF, ZIP, DOCX, PPTX, CSV, code/text files.",
        )
    content = await upload.read()
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(content) > MAX_SUBMISSION_BYTES:
        raise HTTPException(status_code=422, detail="Uploaded file exceeds the 25 MB limit.")

    safe_key = f"{prefix}_{uuid.uuid4().hex}{ext_lower}"
    dest_path = os.path.realpath(os.path.join(target_dir, safe_key))
    if not dest_path.startswith(os.path.realpath(target_dir) + os.sep):
        raise HTTPException(status_code=400, detail="Invalid upload destination")
    with open(dest_path, "wb") as fp:
        fp.write(content)
    return safe_key, raw_name, _format_byte_size(len(content))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _parse_json(raw: str | None, fallback: Any):
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except Exception:
        return fallback


def _initials(name: str | None) -> str:
    parts = [p for p in (name or "").strip().split() if p]
    if not parts:
        return "TR"
    return "".join(p[0] for p in parts)[:2].upper()


def _require_staff(current_user, detail: str = "Only teachers or administrators can perform this action.") -> str:
    role = role_str(current_user)
    if role not in _STAFF_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return role


def _ensure_teacher_scope_for_item(db: Session, current_user, department_id: int | None, cohort_id: int | None) -> None:
    if role_str(current_user) != Role.TEACHER.value:
        return
    resolved_dept_id = department_id
    if resolved_dept_id is None and cohort_id is not None:
        cohort = db.get(Cohort, int(cohort_id))
        if cohort is not None:
            resolved_dept_id = int(cohort.department_id)
    if resolved_dept_id is not None:
        require_teacher_department_access(
            db,
            current_user,
            int(resolved_dept_id),
            allow_common_read=False,
        )
    else:
        allowed = resolve_teacher_scope(db, current_user)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No departments assigned to your teacher account.",
            )


def _fetch_identity_learners(user_ids: list[int] | None = None) -> list[dict[str, Any]]:
    try:
        with IdentitySessionLocal() as id_db:
            stmt = select(IdentityUser).where(
                IdentityUser.role == Role.LEARNER.value,
                IdentityUser.is_active == True,  # noqa: E712
            )
            if user_ids is not None:
                if not user_ids:
                    return []
                stmt = stmt.where(IdentityUser.id.in_(user_ids))
            rows = id_db.scalars(stmt.order_by(IdentityUser.full_name)).all()
            return [
                {
                    "id": int(u.id),
                    "full_name": u.full_name,
                    "email": u.email,
                    "selected_department_id": u.selected_department_id,
                    "department_approved": bool(u.department_approved),
                }
                for u in rows
            ]
    except Exception:
        return []


def _resolve_learner_departments(
    db: Session,
    learner_profiles: list[dict[str, Any]],
) -> dict[int, tuple[int | None, str | None]]:
    """Resolve each learner's concrete (department_id, department_name) from Identity, requests, and cohorts."""
    if not learner_profiles:
        return {}

    dept_map = {
        int(d.id): d.name
        for d in db.scalars(select(Department).where(Department.is_active == True)).all()  # noqa: E712
    }
    learner_ids = [int(lp["id"]) for lp in learner_profiles]

    req_dept_by_user: dict[int, int] = {}
    from services.training.app.models.entities import StudentDepartmentRequest

    req_rows = db.scalars(
        select(StudentDepartmentRequest)
        .where(
            StudentDepartmentRequest.user_id.in_(learner_ids),
            StudentDepartmentRequest.status.in_(["approved", "pending"]),
        )
        .order_by(StudentDepartmentRequest.id.desc())
    ).all()
    for r in req_rows:
        uid = int(r.user_id)
        if uid not in req_dept_by_user and int(r.department_id) in dept_map:
            req_dept_by_user[uid] = int(r.department_id)

    cohort_dept_by_user: dict[int, int] = {}
    cm_rows = db.execute(
        select(CohortMember.user_id, Cohort.department_id)
        .join(Cohort, Cohort.id == CohortMember.cohort_id)
        .where(
            CohortMember.user_id.in_(learner_ids),
            CohortMember.status == "active",
            Cohort.status != "completed",
        )
    ).all()
    for uid, did in cm_rows:
        if int(uid) not in cohort_dept_by_user and int(did) in dept_map:
            cohort_dept_by_user[int(uid)] = int(did)

    resolved: dict[int, tuple[int | None, str | None]] = {}
    for lp in learner_profiles:
        uid = int(lp["id"])
        dept_id: int | None = None
        raw_sel = lp.get("selected_department_id")
        if raw_sel is not None and str(raw_sel).strip().isdigit():
            cand = int(str(raw_sel).strip())
            if cand in dept_map:
                dept_id = cand
        if dept_id is None:
            dept_id = req_dept_by_user.get(uid) or cohort_dept_by_user.get(uid)
        resolved[uid] = (dept_id, dept_map.get(dept_id) if dept_id is not None else None)
    return resolved


def _item_in_scope(
    item_cohort_id: int | None,
    item_dept_id: int | None,
    *,
    requested_cohort_id: int | None,
    allowed_dept_ids: set[int] | None,
    member_cohort_ids: set[int] | None,
) -> bool:
    if requested_cohort_id is not None:
        if item_cohort_id is not None and int(item_cohort_id) != int(requested_cohort_id):
            return False
    if member_cohort_ids is not None and item_cohort_id is not None:
        if int(item_cohort_id) not in member_cohort_ids:
            return False
    if allowed_dept_ids is not None and item_dept_id is not None:
        if int(item_dept_id) not in allowed_dept_ids:
            return False
    return True


def _db_now(db: Session):
    """Use the exact DB clock on MSSQL (matching server_default=func.now()) and microsecond UTC elsewhere."""
    if db.bind is not None and db.bind.dialect.name.lower() == "mssql":
        return func.now()
    return datetime.now(timezone.utc)


def _relative_label(dt: datetime | None) -> str:
    if not dt:
        return "Just now"
    return dt.isoformat()


def _serialize_chapter(ch: CohortChapter, lessons: list[CohortLesson]) -> dict[str, Any]:
    return {
        "id": str(ch.id),
        "backendId": int(ch.id),
        "cohortId": ch.cohort_id,
        "title": ch.title,
        "sequenceOrder": ch.sequence_order,
        "isExpanded": True,
        "departmentId": ch.department_id,
        "departmentName": ch.department_name,
        "lessons": [_serialize_lesson(les) for les in lessons],
    }


def _serialize_lesson(les: CohortLesson) -> dict[str, Any]:
    has_file = bool(getattr(les, "file_storage_key", None))
    dl_url = (
        f"/training-api/api/v1/cohorts/workspace/lessons/{int(les.id)}/file"
        if has_file
        else les.download_url
    )
    return {
        "id": str(les.id),
        "backendId": int(les.id),
        "cohortId": les.cohort_id,
        "title": les.title,
        "type": les.lesson_type,
        "duration": les.duration,
        "description": les.description or "",
        "videoUrl": les.video_url,
        "textNotes": les.text_notes,
        "downloadUrl": dl_url,
        "hasFile": has_file,
        "fileSize": les.file_size,
        "fileName": les.file_name,
        "quizQuestionsCount": les.quiz_questions_count,
        "isPublished": bool(les.is_published),
        "scheduledDate": les.scheduled_date,
        "scheduledTime": les.scheduled_time,
        "meetingUrl": les.meeting_url,
        "isLiveNow": bool(les.is_live_now),
        "trainer": les.trainer_name,
        "departmentId": les.department_id,
        "departmentName": les.department_name,
        "createdAt": _relative_label(les.created_at),
    }


def _build_workspace_payload(
    db: Session,
    current_user,
    cohort_id: int | None = None,
) -> WorkspaceResponse:
    role = role_str(current_user)
    user_id = int(current_user.id)

    allowed_dept_ids: set[int] | None = None
    member_cohort_ids: set[int] | None = None
    learner_unapproved = False

    if role == Role.LEARNER.value:
        allowed = get_learner_allowed_dept_ids(db, user_id)
        if allowed is None:
            learner_unapproved = True
            allowed_dept_ids = set()
        else:
            common_ids = get_common_department_ids(db)
            concrete_only = {int(d) for d in allowed if int(d) not in common_ids}
            allowed_dept_ids = concrete_only if concrete_only else set(allowed)
        member_cohort_ids = {
            int(cid)
            for cid in db.scalars(
                select(CohortMember.cohort_id).where(
                    CohortMember.user_id == user_id,
                    CohortMember.status == "active",
                )
            ).all()
        }
    elif role == Role.TEACHER.value:
        teacher_depts = resolve_teacher_scope(db, current_user) or set()
        common_ids = get_common_department_ids(db)
        allowed_dept_ids = teacher_depts | common_ids

    if learner_unapproved:
        return WorkspaceResponse(
            curriculum=[],
            assignments=[],
            quizzes=[],
            announcements=[],
            discussions=[],
            attendance={
                "percentage": 0,
                "totalSessions": 0,
                "attended": 0,
                "missed": 0,
                "excused": 0,
                "late": 0,
                "minimumRequired": 85,
                "checkedInToday": False,
                "history": [],
            },
            attendanceMatrix={"dateRangeLabel": "", "days": [], "students": []},
            progress={
                "overallPercentage": 0,
                "modulesCompleted": 0,
                "totalModules": 0,
                "assignmentsSubmitted": 0,
                "totalAssignments": 0,
                "quizzesPassed": 0,
                "totalQuizzes": 0,
                "attendanceRate": 0,
                "milestones": [],
                "earnedBadges": [],
            },
            bookmarkedMaterialKeys=[],
        )

    # 1. Curriculum (Chapters & Lessons)
    all_chapters = db.scalars(
        select(CohortChapter).order_by(CohortChapter.sequence_order.asc(), CohortChapter.id.asc())
    ).all()
    scoped_chapters = [
        ch
        for ch in all_chapters
        if _item_in_scope(
            ch.cohort_id,
            ch.department_id,
            requested_cohort_id=cohort_id,
            allowed_dept_ids=allowed_dept_ids,
            member_cohort_ids=member_cohort_ids,
        )
    ]
    chap_ids = [int(c.id) for c in scoped_chapters]
    lessons_by_chap: dict[int, list[CohortLesson]] = {}
    if chap_ids:
        for les in db.scalars(
            select(CohortLesson)
            .where(CohortLesson.chapter_id.in_(chap_ids))
            .order_by(CohortLesson.created_at.desc(), CohortLesson.id.desc())
        ).all():
            # Live sessions live in Schedule/Cohort Details and Assignments live in Assignments — never in Curriculum/Materials
            if (les.lesson_type or "").lower() in {"live", "assignment", "quiz"}:
                continue
            if _item_in_scope(
                les.cohort_id,
                les.department_id,
                requested_cohort_id=cohort_id,
                allowed_dept_ids=allowed_dept_ids,
                member_cohort_ids=member_cohort_ids,
            ):
                lessons_by_chap.setdefault(int(les.chapter_id), []).append(les)
    curriculum = [
        _serialize_chapter(ch, lessons_by_chap.get(int(ch.id), []))
        for ch in scoped_chapters
    ]

    # 2. Assignments + Submissions
    raw_assignments = db.scalars(
        select(CohortAssignment).order_by(CohortAssignment.id.desc())
    ).all()
    scoped_assignments = [
        a
        for a in raw_assignments
        if _item_in_scope(
            a.cohort_id,
            a.department_id,
            requested_cohort_id=cohort_id,
            allowed_dept_ids=allowed_dept_ids,
            member_cohort_ids=member_cohort_ids,
        )
    ]
    asg_ids = [int(a.id) for a in scoped_assignments]
    subs_by_asg: dict[int, list[CohortAssignmentSubmission]] = {}
    if asg_ids:
        for sub in db.scalars(
            select(CohortAssignmentSubmission)
            .where(CohortAssignmentSubmission.assignment_id.in_(asg_ids))
            .order_by(CohortAssignmentSubmission.submitted_at.desc())
        ).all():
            subs_by_asg.setdefault(int(sub.assignment_id), []).append(sub)

    assignments_out: list[dict[str, Any]] = []
    submitted_or_graded_count = 0
    for a in scoped_assignments:
        asg_subs = subs_by_asg.get(int(a.id), [])
        user_sub = next((s for s in asg_subs if int(s.learner_user_id) == user_id), None)
        display_sub = user_sub if role == Role.LEARNER.value else (user_sub or (asg_subs[0] if asg_subs else None))
        status_val = display_sub.status if display_sub else "pending"
        if display_sub and display_sub.status in ("submitted", "graded"):
            submitted_or_graded_count += 1
        due_rel = (
            f"Graded ({display_sub.score}/{a.points})"
            if display_sub and display_sub.status == "graded"
            else ("Submitted — Under Review" if display_sub and display_sub.status == "submitted" else f"Due on {a.due_date or 'TBD'}")
        )
        has_att_file = bool(getattr(a, "attachment_storage_key", None))
        resolved_att_url = (
            f"/training-api/api/v1/cohorts/workspace/assignments/{int(a.id)}/attachment"
            if has_att_file
            else a.attachment_url
        )
        assignments_out.append(
            {
                "id": str(a.id),
                "backendId": int(a.id),
                "cohortId": a.cohort_id,
                "title": a.title,
                "module": a.module,
                "description": a.description,
                "points": a.points,
                "dueDate": a.due_date,
                "dueRelative": due_rel,
                "status": status_val,
                "attachmentName": a.attachment_name,
                "attachmentUrl": resolved_att_url,
                "attachmentSize": a.attachment_size,
                "hasAttachmentFile": has_att_file,
                "submissionId": int(display_sub.id) if display_sub else None,
                "submissionDate": _relative_label(display_sub.submitted_at) if display_sub else None,
                "submissionUrl": display_sub.submission_url if display_sub else None,
                "submissionNotes": display_sub.submission_notes if display_sub else None,
                "submissionFileName": getattr(display_sub, "submission_file_name", None) if display_sub else None,
                "hasSubmissionFile": bool(display_sub and getattr(display_sub, "submission_file_storage_key", None)),
                "score": display_sub.score if display_sub else None,
                "trainerFeedback": display_sub.trainer_feedback if display_sub else None,
                "learnerUserId": int(display_sub.learner_user_id) if display_sub else None,
                "learnerName": display_sub.learner_name if display_sub else None,
                "requirements": _parse_json(a.requirements_json, []),
                "departmentId": a.department_id,
                "departmentName": a.department_name,
                "submissions": [
                    {
                        "id": int(s.id),
                        "learnerUserId": int(s.learner_user_id),
                        "learnerName": s.learner_name,
                        "learnerEmail": s.learner_email,
                        "status": s.status,
                        "submissionUrl": s.submission_url,
                        "submissionNotes": s.submission_notes,
                        "submissionFileName": getattr(s, "submission_file_name", None),
                        "hasSubmissionFile": bool(getattr(s, "submission_file_storage_key", None)),
                        "submittedAt": _relative_label(s.submitted_at),
                        "score": s.score,
                        "trainerFeedback": s.trainer_feedback,
                    }
                    for s in (asg_subs if role in _STAFF_ROLES else ([user_sub] if user_sub else []))
                ],
            }
        )

    # 3. Quizzes + Submissions
    raw_quizzes = db.scalars(select(CohortQuiz).order_by(CohortQuiz.id.desc())).all()
    scoped_quizzes = [
        q
        for q in raw_quizzes
        if _item_in_scope(
            q.cohort_id,
            q.department_id,
            requested_cohort_id=cohort_id,
            allowed_dept_ids=allowed_dept_ids,
            member_cohort_ids=member_cohort_ids,
        )
    ]
    q_ids = [int(q.id) for q in scoped_quizzes]
    q_subs_by_quiz: dict[int, list[CohortQuizSubmission]] = {}
    if q_ids:
        for qs in db.scalars(
            select(CohortQuizSubmission)
            .where(CohortQuizSubmission.quiz_id.in_(q_ids))
            .order_by(CohortQuizSubmission.submitted_at.desc())
        ).all():
            q_subs_by_quiz.setdefault(int(qs.quiz_id), []).append(qs)

    quizzes_out: list[dict[str, Any]] = []
    quizzes_passed_count = 0
    for q in scoped_quizzes:
        q_subs = q_subs_by_quiz.get(int(q.id), [])
        user_qsub = next((s for s in q_subs if int(s.learner_user_id) == user_id), None)
        if user_qsub and user_qsub.passed:
            quizzes_passed_count += 1
        visible_subs = q_subs if role in _STAFF_ROLES else ([user_qsub] if user_qsub else [])
        quizzes_out.append(
            {
                "id": str(q.id),
                "backendId": int(q.id),
                "cohortId": q.cohort_id,
                "title": q.title,
                "module": q.module,
                "questionsCount": q.questions_count,
                "durationMinutes": q.duration_minutes,
                "dueDate": q.due_date,
                "passingScore": q.passing_score,
                "status": "completed" if user_qsub else "available",
                "attachmentName": q.attachment_name,
                "attachmentUrl": q.attachment_url,
                "attachmentSize": q.attachment_size,
                "score": user_qsub.score if user_qsub else None,
                "passed": bool(user_qsub.passed) if user_qsub else None,
                "completedAt": _relative_label(user_qsub.submitted_at) if user_qsub else None,
                "questions": _parse_json(q.questions_json, []),
                "departmentId": q.department_id,
                "departmentName": q.department_name,
                "submissions": [
                    {
                        "studentId": int(s.learner_user_id),
                        "studentName": s.learner_name,
                        "studentEmail": s.learner_email,
                        "score": s.score,
                        "passed": bool(s.passed),
                        "submittedAt": _relative_label(s.submitted_at),
                    }
                    for s in visible_subs
                ],
            }
        )

    # 4. Announcements
    raw_anns = db.scalars(
        select(CohortAnnouncement).order_by(CohortAnnouncement.is_pinned.desc(), CohortAnnouncement.id.desc())
    ).all()
    scoped_anns = [
        ann
        for ann in raw_anns
        if _item_in_scope(
            ann.cohort_id,
            ann.department_id,
            requested_cohort_id=cohort_id,
            allowed_dept_ids=allowed_dept_ids,
            member_cohort_ids=member_cohort_ids,
        )
    ]
    read_ann_ids = {
        int(aid)
        for aid in db.scalars(
            select(CohortAnnouncementRead.announcement_id).where(CohortAnnouncementRead.user_id == user_id)
        ).all()
    }
    announcements_out = [
        {
            "id": str(ann.id),
            "backendId": int(ann.id),
            "cohortId": ann.cohort_id,
            "departmentId": ann.department_id,
            "title": ann.title,
            "author": ann.author_name,
            "authorRole": ann.author_role,
            "authorAvatar": ann.author_avatar,
            "date": _relative_label(ann.created_at),
            "priority": ann.priority,
            "isPinned": bool(ann.is_pinned),
            "isRead": int(ann.id) in read_ann_ids,
            "content": ann.content,
            "tags": _parse_json(ann.tags_json, []),
        }
        for ann in scoped_anns
    ]

    # 5. Discussions + Replies + Likes
    raw_discs = db.scalars(select(CohortDiscussion).order_by(CohortDiscussion.id.desc())).all()
    scoped_discs = [
        d
        for d in raw_discs
        if _item_in_scope(
            d.cohort_id,
            d.department_id,
            requested_cohort_id=cohort_id,
            allowed_dept_ids=allowed_dept_ids,
            member_cohort_ids=member_cohort_ids,
        )
    ]
    disc_ids = [int(d.id) for d in scoped_discs]
    replies_by_disc: dict[int, list[CohortDiscussionReply]] = {}
    likes_by_disc: dict[int, set[int]] = {}
    if disc_ids:
        for rep in db.scalars(
            select(CohortDiscussionReply)
            .where(CohortDiscussionReply.discussion_id.in_(disc_ids))
            .order_by(CohortDiscussionReply.id.asc())
        ).all():
            replies_by_disc.setdefault(int(rep.discussion_id), []).append(rep)
        for lk in db.scalars(
            select(CohortDiscussionLike).where(CohortDiscussionLike.discussion_id.in_(disc_ids))
        ).all():
            likes_by_disc.setdefault(int(lk.discussion_id), set()).add(int(lk.user_id))

    discussions_out = [
        {
            "id": str(d.id),
            "backendId": int(d.id),
            "cohortId": d.cohort_id,
            "departmentId": d.department_id,
            "title": d.title,
            "category": d.category,
            "author": d.author_name,
            "authorRole": d.author_role,
            "authorAvatar": d.author_avatar,
            "createdAt": _relative_label(d.created_at),
            "content": d.content,
            "likes": len(likes_by_disc.get(int(d.id), set())),
            "hasLiked": user_id in likes_by_disc.get(int(d.id), set()),
            "isResolved": bool(d.is_resolved),
            "replies": [
                {
                    "id": str(r.id),
                    "author": r.author_name,
                    "authorRole": r.author_role,
                    "authorAvatar": r.author_avatar,
                    "createdAt": _relative_label(r.created_at),
                    "content": r.content,
                    "isTrainerReply": bool(r.is_trainer_reply),
                }
                for r in replies_by_disc.get(int(d.id), [])
            ],
        }
        for d in scoped_discs
    ]

    # 6. Attendance Matrix (rolling 14-day window ending today)
    today_dt = date.today()
    days_list: list[dict[str, Any]] = []
    day_letters = ["M", "T", "W", "T", "F", "S", "S"]
    for offset in range(13, -1, -1):
        d_val = today_dt - timedelta(days=offset)
        days_list.append(
            {
                "dateStr": d_val.isoformat(),
                "dayLetter": day_letters[d_val.weekday()],
                "dateNum": f"{d_val.day:02d}",
                "isWeekend": d_val.weekday() >= 5,
            }
        )
    date_range_label = f"{(today_dt - timedelta(days=13)).strftime('%d %b')} - {today_dt.strftime('%d %b %Y')}"

    if role == Role.LEARNER.value:
        learner_profiles = _fetch_identity_learners([user_id])
        learner_dept_map = _resolve_learner_departments(db, learner_profiles)
    elif role in {Role.SUPERADMIN.value, Role.ADMIN.value}:
        # SuperAdmin & Admin see ALL active students across ALL departments in Attendance
        learner_profiles = _fetch_identity_learners()
        learner_dept_map = _resolve_learner_departments(db, learner_profiles)
    elif role == Role.TEACHER.value:
        # Teachers strictly see ONLY students belonging to their assigned department(s)
        all_profiles = _fetch_identity_learners()
        learner_dept_map = _resolve_learner_departments(db, all_profiles)
        if allowed_dept_ids:
            learner_profiles = [
                lp
                for lp in all_profiles
                if learner_dept_map.get(int(lp["id"]), (None, None))[0] in allowed_dept_ids
            ]
        else:
            learner_profiles = []
    else:
        learner_profiles = []
        learner_dept_map = {}

    att_stmt = select(CohortAttendanceEntry)
    if cohort_id is not None and role == Role.LEARNER.value:
        att_stmt = att_stmt.where(
            (CohortAttendanceEntry.cohort_id == int(cohort_id)) | (CohortAttendanceEntry.cohort_id.is_(None))
        )
    att_entries = db.scalars(att_stmt).all()
    att_map: dict[tuple[int, str], CohortAttendanceEntry] = {
        (int(e.learner_user_id), e.attendance_date): e for e in att_entries
    }

    matrix_students: list[dict[str, Any]] = []
    for lp in learner_profiles:
        lid = int(lp["id"])
        dept_id, dept_name = learner_dept_map.get(lid, (None, None))
        daily_status: dict[str, str] = {}
        abs_cnt = 0
        lve_cnt = 0
        for d_item in days_list:
            ds = d_item["dateStr"]
            entry = att_map.get((lid, ds))
            if entry:
                st = entry.status
            elif d_item["isWeekend"]:
                st = "H"
            else:
                st = "P"
            daily_status[ds] = st
            if st == "A":
                abs_cnt += 1
            elif st == "L":
                lve_cnt += 1
        matrix_students.append(
            {
                "studentId": f"std-{lid}",
                "backendUserId": lid,
                "admissionNo": f"LRN/2026/{lid:04d}",
                "name": lp["full_name"],
                "email": lp.get("email") or "",
                "departmentId": dept_id,
                "departmentName": dept_name,
                "absCount": abs_cnt,
                "lveCount": lve_cnt,
                "dailyStatus": daily_status,
            }
        )

    # Learner / current user attendance summary
    today_iso = today_dt.isoformat()
    user_entries = [e for e in att_entries if int(e.learner_user_id) == user_id]
    attended_cnt = sum(1 for e in user_entries if e.status == "P")
    missed_cnt = sum(1 for e in user_entries if e.status == "A")
    late_cnt = sum(1 for e in user_entries if e.status == "L")
    excused_cnt = sum(1 for e in user_entries if e.status == "H")
    total_att = len(user_entries)
    pct = round((attended_cnt / total_att) * 100) if total_att > 0 else 0
    checked_in_today = (user_id, today_iso) in att_map and att_map[(user_id, today_iso)].status == "P"

    attendance_summary = {
        "percentage": pct,
        "totalSessions": total_att,
        "attended": attended_cnt,
        "missed": missed_cnt,
        "excused": excused_cnt,
        "late": late_cnt,
        "minimumRequired": 85,
        "checkedInToday": checked_in_today,
        "history": [
            {
                "sessionId": f"att-{e.id}",
                "sessionTitle": e.session_title or "Cohort Training Session",
                "date": e.attendance_date,
                "status": "present" if e.status == "P" else ("absent" if e.status == "A" else "late"),
                "recordedAt": _relative_label(e.updated_at),
                "recordedBy": e.recorded_by_name or "Instructor",
            }
            for e in sorted(user_entries, key=lambda x: x.attendance_date, reverse=True)
        ],
    }

    # 7. Bookmarks
    bookmarked_keys = list(
        db.scalars(
            select(CohortMaterialBookmark.material_key).where(CohortMaterialBookmark.user_id == user_id)
        ).all()
    )

    # 8. Delivered Course Resource Vault materials for active batches in caller's scope
    delivered_materials_out: list[dict[str, Any]] = []
    deliv_stmt = (
        select(CohortMaterialDelivery, LearningMaterial, Cohort, Course)
        .join(LearningMaterial, LearningMaterial.id == CohortMaterialDelivery.material_id)
        .join(Cohort, Cohort.id == CohortMaterialDelivery.cohort_id)
        .join(Course, Course.id == CohortMaterialDelivery.course_id)
        .where(
            LearningMaterial.is_active == True,  # noqa: E712
            Cohort.status != "completed",
        )
        .order_by(CohortMaterialDelivery.sent_at.desc(), CohortMaterialDelivery.id.desc())
    )
    deliv_rows = db.execute(deliv_stmt).all()
    if deliv_rows:
        dept_rows = db.scalars(select(Department)).all()
        dept_name_by_id = {int(d.id): d.name for d in dept_rows}

        teacher_assigned_cohorts: set[int] = set()
        cohorts_with_explicit_teachers: set[int] = set()
        if role == Role.TEACHER.value:
            all_ct = db.scalars(select(CohortTeacher)).all()
            for ct in all_ct:
                cohorts_with_explicit_teachers.add(int(ct.cohort_id))
                if int(ct.user_id) == user_id:
                    teacher_assigned_cohorts.add(int(ct.cohort_id))

        sender_ids = {int(deliv.sent_by_user_id) for deliv, _, _, _ in deliv_rows}
        sender_name_map: dict[int, str] = {}
        if sender_ids:
            try:
                with IdentitySessionLocal() as id_db:
                    for u in id_db.scalars(
                        select(IdentityUser).where(IdentityUser.id.in_(list(sender_ids)))
                    ).all():
                        sender_name_map[int(u.id)] = u.full_name
            except Exception:
                pass

        for deliv, mat, cohort_row, course_row in deliv_rows:
            c_id = int(cohort_row.id)
            c_dept_id = int(cohort_row.department_id)
            if role == Role.LEARNER.value:
                if member_cohort_ids is None or c_id not in member_cohort_ids:
                    continue
                if allowed_dept_ids is None or c_dept_id not in allowed_dept_ids:
                    continue
            elif role == Role.TEACHER.value:
                if allowed_dept_ids is None or c_dept_id not in allowed_dept_ids:
                    continue
                if c_id in cohorts_with_explicit_teachers and c_id not in teacher_assigned_cohorts:
                    continue

            delivered_materials_out.append(
                {
                    "id": int(deliv.id),
                    "cohort_id": c_id,
                    "cohort_name": cohort_row.name,
                    "course_id": int(deliv.course_id),
                    "material_id": int(mat.id),
                    "title": mat.title,
                    "material_type": mat.material_type,
                    "storage_key": mat.storage_key,
                    "department_id": c_dept_id,
                    "department_name": dept_name_by_id.get(c_dept_id, ""),
                    "source_department_name": dept_name_by_id.get(int(course_row.department_id), ""),
                    "sent_by_user_id": int(deliv.sent_by_user_id),
                    "sent_by_name": sender_name_map.get(int(deliv.sent_by_user_id), "Instructor"),
                    "sent_at": _relative_label(deliv.sent_at),
                }
            )

    total_chaps = len(curriculum)
    total_asgs = len(assignments_out)
    total_qzs = len(quizzes_out)
    progress = {
        "overallPercentage": pct,
        "modulesCompleted": 0,
        "totalModules": total_chaps,
        "assignmentsSubmitted": submitted_or_graded_count,
        "totalAssignments": total_asgs,
        "quizzesPassed": quizzes_passed_count,
        "totalQuizzes": total_qzs,
        "attendanceRate": pct,
        "milestones": [],
        "earnedBadges": [],
    }

    return WorkspaceResponse(
        curriculum=curriculum,
        assignments=assignments_out,
        quizzes=quizzes_out,
        announcements=announcements_out,
        discussions=discussions_out,
        attendance=attendance_summary,
        attendanceMatrix={
            "dateRangeLabel": date_range_label,
            "days": days_list,
            "students": matrix_students,
        },
        progress=progress,
        bookmarkedMaterialKeys=bookmarked_keys,
        deliveredMaterials=delivered_materials_out,
    )


@router.get("", response_model=WorkspaceResponse)
def get_workspace(
    cohort_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _build_workspace_payload(db, current_user, cohort_id=cohort_id)


@router.post("/chapters", status_code=status.HTTP_201_CREATED)
def create_chapter(
    payload: ChapterCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    _ensure_teacher_scope_for_item(db, current_user, payload.department_id, payload.cohort_id)

    dept_name = payload.department_name
    if payload.department_id is not None:
        dept = db.get(Department, int(payload.department_id))
        if dept is not None:
            dept_name = dept.name

    existing_count = len(db.scalars(select(CohortChapter.id)).all())
    ch = CohortChapter(
        cohort_id=payload.cohort_id,
        department_id=payload.department_id,
        department_name=dept_name or "All / Common",
        title=payload.title.strip(),
        sequence_order=existing_count + 1,
        created_by_user_id=int(current_user.id),
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return _serialize_chapter(ch, [])


@router.delete("/chapters/{chapter_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chapter(
    chapter_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    ch = db.get(CohortChapter, chapter_id)
    if ch is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    _ensure_teacher_scope_for_item(db, current_user, ch.department_id, ch.cohort_id)
    db.delete(ch)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/chapters/{chapter_id}/lessons", status_code=status.HTTP_201_CREATED)
def create_lesson(
    chapter_id: int,
    payload: LessonCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    ch = db.get(CohortChapter, chapter_id)
    if ch is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    resolved_dept_id = payload.department_id if payload.department_id is not None else ch.department_id
    resolved_cohort_id = payload.cohort_id if payload.cohort_id is not None else ch.cohort_id
    _ensure_teacher_scope_for_item(db, current_user, resolved_dept_id, resolved_cohort_id)

    dept_name = payload.department_name or ch.department_name or "All / Common"
    if resolved_dept_id is not None:
        dept = db.get(Department, int(resolved_dept_id))
        if dept is not None:
            dept_name = dept.name

    # Assignments go strictly to Assignments tab (never into Curriculum & Materials)
    if payload.type == "assignment":
        asg = CohortAssignment(
            cohort_id=resolved_cohort_id,
            department_id=resolved_dept_id,
            department_name=dept_name,
            title=payload.title.strip(),
            module=ch.title,
            description=payload.description or "Complete the practical task according to rubric.",
            points=payload.points or 100,
            due_date=payload.scheduled_date or (date.today() + timedelta(days=7)).isoformat(),
            requirements_json=json.dumps(["Code implementation meeting specification", "Unit tests passing 85%+"]),
            attachment_name=payload.file_name,
            attachment_url=payload.download_url if payload.download_url and payload.download_url != "#" else None,
            attachment_size=payload.file_size,
            created_by_user_id=int(current_user.id),
        )
        db.add(asg)
        db.commit()
        db.refresh(asg)
        return {
            "id": str(asg.id),
            "backendId": int(asg.id),
            "assignmentId": int(asg.id),
            "type": "assignment",
            "title": asg.title,
        }

    # Live sessions live strictly in Schedule & Cohort Details (via /api/v1/live-classes)
    if payload.type == "live":
        return {
            "id": f"live-routed-{ch.id}",
            "type": "live",
            "title": payload.title.strip(),
            "routed_to": "schedule",
        }

    duration = payload.duration if payload.type == "video" else None
    if payload.type == "video":
        duration = duration or "15:00"

    les = CohortLesson(
        chapter_id=ch.id,
        cohort_id=resolved_cohort_id,
        department_id=resolved_dept_id,
        department_name=dept_name,
        title=payload.title.strip(),
        lesson_type=payload.type,
        duration=duration,
        description=payload.description or "",
        video_url=payload.video_url,
        text_notes=payload.text_notes,
        download_url=payload.download_url,
        file_size=payload.file_size,
        file_name=payload.file_name,
        quiz_questions_count=payload.quiz_questions_count,
        is_published=True,
        scheduled_date=payload.scheduled_date,
        scheduled_time=payload.scheduled_time,
        meeting_url=payload.meeting_url,
        is_live_now=False,
        trainer_name=payload.trainer or current_user.full_name,
        created_by_user_id=int(current_user.id),
        created_at=_db_now(db),
    )
    db.add(les)
    db.commit()
    db.refresh(les)
    return _serialize_lesson(les)


@router.post("/chapters/{chapter_id}/lessons/upload", status_code=status.HTTP_201_CREATED)
async def upload_downloadable_lesson(
    chapter_id: int,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(default=""),
    cohort_id: int | None = Form(default=None),
    department_id: int | None = Form(default=None),
    department_name: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload a teacher file strictly as a Downloadable curriculum resource."""
    _require_staff(current_user)
    ch = db.get(CohortChapter, chapter_id)
    if ch is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    resolved_dept_id = department_id if department_id is not None else ch.department_id
    resolved_cohort_id = cohort_id if cohort_id is not None else ch.cohort_id
    _ensure_teacher_scope_for_item(db, current_user, resolved_dept_id, resolved_cohort_id)

    dept_name_val = department_name.strip() or ch.department_name or "All / Common"
    if resolved_dept_id is not None:
        dept = db.get(Department, int(resolved_dept_id))
        if dept is not None:
            dept_name_val = dept.name

    safe_key, orig_name, size_str = await _save_uploaded_file(
        file,
        COHORT_DOWNLOADABLES_DIR,
        f"les_ch{chapter_id}_u{int(current_user.id)}",
        ALLOWED_RESOURCE_EXTENSIONS,
    )

    les = CohortLesson(
        chapter_id=ch.id,
        cohort_id=resolved_cohort_id,
        department_id=resolved_dept_id,
        department_name=dept_name_val,
        title=title.strip() or orig_name,
        lesson_type="download",
        duration=None,
        description=description.strip(),
        download_url=None,
        file_size=size_str,
        file_name=orig_name,
        file_storage_key=safe_key,
        is_published=True,
        trainer_name=current_user.full_name,
        created_by_user_id=int(current_user.id),
        created_at=_db_now(db),
    )
    db.add(les)
    db.commit()
    db.refresh(les)
    les.download_url = f"/training-api/api/v1/cohorts/workspace/lessons/{int(les.id)}/file"
    db.commit()
    db.refresh(les)
    return _serialize_lesson(les)


@router.get("/lessons/{lesson_id}/file")
def download_lesson_file(
    lesson_id: int,
    inline: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    les = db.get(CohortLesson, lesson_id)
    if les is None or not getattr(les, "file_storage_key", None):
        raise HTTPException(status_code=404, detail="Downloadable file not found")
    role = role_str(current_user)
    if role == Role.TEACHER.value:
        _ensure_teacher_scope_for_item(db, current_user, les.department_id, les.cohort_id)
    elif role == Role.LEARNER.value:
        allowed = get_learner_allowed_dept_ids(db, int(current_user.id))
        if allowed is None:
            raise HTTPException(status_code=403, detail="Department approval required to download cohort files.")
        if les.department_id is not None and int(les.department_id) not in allowed:
            raise HTTPException(status_code=403, detail="File belongs to another department.")
    elif role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Unauthorized")

    file_path = os.path.realpath(os.path.join(COHORT_DOWNLOADABLES_DIR, os.path.basename(les.file_storage_key)))
    if not file_path.startswith(os.path.realpath(COHORT_DOWNLOADABLES_DIR) + os.sep) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File missing on server")
    import mimetypes

    display_name = les.file_name or os.path.basename(les.file_storage_key)
    guessed_mime, _ = mimetypes.guess_type(display_name)
    media_type = "application/pdf" if display_name.lower().endswith(".pdf") else (guessed_mime or "application/octet-stream")
    if inline:
        safe_disp_name = display_name.replace('"', "")
        return FileResponse(
            path=file_path,
            media_type=media_type,
            headers={"Content-Disposition": f'inline; filename="{safe_disp_name}"'},
        )
    return FileResponse(
        path=file_path,
        filename=display_name,
        media_type=media_type,
    )


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    les = db.get(CohortLesson, lesson_id)
    if les is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _ensure_teacher_scope_for_item(db, current_user, les.department_id, les.cohort_id)
    db.delete(les)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/lessons/{lesson_id}/toggle-live")
def toggle_lesson_live(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    les = db.get(CohortLesson, lesson_id)
    if les is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    _ensure_teacher_scope_for_item(db, current_user, les.department_id, les.cohort_id)
    les.is_live_now = not bool(les.is_live_now)
    db.commit()
    db.refresh(les)
    return _serialize_lesson(les)


@router.post("/assignments", status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    _ensure_teacher_scope_for_item(db, current_user, payload.department_id, payload.cohort_id)

    dept_name = payload.department_name
    if payload.department_id is not None:
        dept = db.get(Department, int(payload.department_id))
        if dept is not None:
            dept_name = dept.name

    asg = CohortAssignment(
        cohort_id=payload.cohort_id,
        department_id=payload.department_id,
        department_name=dept_name or "All / Common",
        title=payload.title.strip(),
        module=payload.module.strip(),
        description=payload.description.strip(),
        points=payload.points,
        due_date=payload.due_date,
        requirements_json=json.dumps(payload.requirements or ["Implement required functionality"]),
        created_by_user_id=int(current_user.id),
    )
    db.add(asg)
    db.commit()
    db.refresh(asg)
    return {"id": str(asg.id), "backendId": int(asg.id), "title": asg.title}


@router.post("/assignments/with-file", status_code=status.HTTP_201_CREATED)
async def create_assignment_with_file(
    title: str = Form(...),
    module: str = Form(default="Core Module"),
    description: str = Form(default=""),
    points: int = Form(default=100),
    due_date: str = Form(default=""),
    requirements: str = Form(default="[]"),
    cohort_id: int | None = Form(default=None),
    department_id: int | None = Form(default=None),
    department_name: str = Form(default="All / Common"),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a CohortAssignment with an optional teacher-uploaded downloadable PDF or reference file."""
    _require_staff(current_user)
    _ensure_teacher_scope_for_item(db, current_user, department_id, cohort_id)

    dept_name_val = department_name.strip() or "All / Common"
    if department_id is not None:
        dept = db.get(Department, int(department_id))
        if dept is not None:
            dept_name_val = dept.name

    req_list = _parse_json(requirements, None)
    if not isinstance(req_list, list):
        req_list = [line.strip() for line in (requirements or "").splitlines() if line.strip()]
    if not req_list:
        req_list = ["Implement required functionality"]

    stored_key: str | None = None
    orig_name: str | None = None
    size_str: str | None = None
    if file is not None and file.filename:
        stored_key, orig_name, size_str = await _save_uploaded_file(
            file,
            ASSIGNMENT_ATTACHMENTS_DIR,
            f"asg_att_u{int(current_user.id)}",
            ALLOWED_RESOURCE_EXTENSIONS,
        )

    asg = CohortAssignment(
        cohort_id=cohort_id,
        department_id=department_id,
        department_name=dept_name_val,
        title=title.strip(),
        module=module.strip() or "Core Module",
        description=description.strip() or "Complete the practical task according to rubric.",
        points=max(1, int(points or 100)),
        due_date=due_date.strip() or (date.today() + timedelta(days=7)).isoformat(),
        requirements_json=json.dumps(req_list),
        attachment_name=orig_name,
        attachment_size=size_str,
        attachment_storage_key=stored_key,
        created_by_user_id=int(current_user.id),
    )
    db.add(asg)
    db.commit()
    db.refresh(asg)
    if stored_key:
        asg.attachment_url = f"/training-api/api/v1/cohorts/workspace/assignments/{int(asg.id)}/attachment"
        db.commit()
        db.refresh(asg)

    return {
        "id": str(asg.id),
        "backendId": int(asg.id),
        "title": asg.title,
        "attachmentName": asg.attachment_name,
        "attachmentUrl": asg.attachment_url,
        "attachmentSize": asg.attachment_size,
        "hasAttachmentFile": bool(stored_key),
    }


@router.get("/assignments/{assignment_id}/attachment")
def download_assignment_attachment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asg = db.get(CohortAssignment, assignment_id)
    if asg is None or not getattr(asg, "attachment_storage_key", None):
        raise HTTPException(status_code=404, detail="Assignment attachment not found")
    role = role_str(current_user)
    if role == Role.TEACHER.value:
        _ensure_teacher_scope_for_item(db, current_user, asg.department_id, asg.cohort_id)
    elif role == Role.LEARNER.value:
        allowed = get_learner_allowed_dept_ids(db, int(current_user.id))
        if allowed is None:
            raise HTTPException(status_code=403, detail="Department approval required to download assignment files.")
        if asg.department_id is not None and int(asg.department_id) not in allowed:
            raise HTTPException(status_code=403, detail="Assignment belongs to another department.")
    elif role not in _STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Unauthorized")

    file_path = os.path.realpath(
        os.path.join(ASSIGNMENT_ATTACHMENTS_DIR, os.path.basename(asg.attachment_storage_key))
    )
    if not file_path.startswith(os.path.realpath(ASSIGNMENT_ATTACHMENTS_DIR) + os.sep) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Attachment file missing on server")
    return FileResponse(
        path=file_path,
        filename=asg.attachment_name or os.path.basename(asg.attachment_storage_key),
        media_type="application/octet-stream",
    )


@router.post("/assignments/{assignment_id}/submit")
def submit_assignment(
    assignment_id: int,
    payload: AssignmentSubmitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asg = db.get(CohortAssignment, assignment_id)
    if asg is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    sub = db.scalar(
        select(CohortAssignmentSubmission).where(
            CohortAssignmentSubmission.assignment_id == assignment_id,
            CohortAssignmentSubmission.learner_user_id == int(current_user.id),
        )
    )
    if sub is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assignment has already been submitted and is permanently locked. Resubmission or editing is not permitted.",
        )

    sub = CohortAssignmentSubmission(
        assignment_id=assignment_id,
        learner_user_id=int(current_user.id),
        learner_name=current_user.full_name,
        learner_email=current_user.email,
        status="submitted",
        submission_url=payload.submission_url.strip(),
        submission_notes=payload.submission_notes.strip(),
        trainer_feedback="Submission received and locked for manual trainer evaluation.",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {"id": int(sub.id), "status": sub.status}


@router.post("/assignments/{assignment_id}/submit-file")
async def submit_assignment_with_file(
    assignment_id: int,
    file: UploadFile | None = File(default=None),
    submission_url: str = Form(default=""),
    submission_notes: str = Form(default=""),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asg = db.get(CohortAssignment, assignment_id)
    if asg is None:
        raise HTTPException(status_code=404, detail="Assignment not found")

    existing = db.scalar(
        select(CohortAssignmentSubmission).where(
            CohortAssignmentSubmission.assignment_id == assignment_id,
            CohortAssignmentSubmission.learner_user_id == int(current_user.id),
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assignment has already been submitted and is permanently locked. Resubmission or editing is not permitted.",
        )

    clean_url = (submission_url or "").strip()
    clean_notes = (submission_notes or "").strip()
    stored_key: str | None = None
    original_name: str | None = None

    if file is not None and file.filename:
        raw_name = os.path.basename(file.filename.strip())
        _, ext = os.path.splitext(raw_name)
        ext_lower = ext.lower()
        if ext_lower not in ALLOWED_SUBMISSION_EXTENSIONS:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported file type '{ext_lower}'. Allowed: .zip, .tar.gz, .7z, .rar, .pdf, code files.",
            )
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=422, detail="Uploaded archive file is empty.")
        if len(content) > MAX_SUBMISSION_BYTES:
            raise HTTPException(status_code=422, detail="Submission file exceeds the 25 MB limit.")

        safe_key = f"asg_{assignment_id}_u{int(current_user.id)}_{uuid.uuid4().hex}{ext_lower}"
        dest_path = os.path.realpath(os.path.join(ASSIGNMENT_SUBMISSIONS_DIR, safe_key))
        if not dest_path.startswith(os.path.realpath(ASSIGNMENT_SUBMISSIONS_DIR) + os.sep):
            raise HTTPException(status_code=400, detail="Invalid upload destination")
        with open(dest_path, "wb") as fp:
            fp.write(content)
        stored_key = safe_key
        original_name = raw_name

    if not clean_url and not stored_key:
        raise HTTPException(
            status_code=422,
            detail="Provide a GitHub/repository link or upload a .zip submission archive.",
        )

    effective_url = (
        clean_url
        or f"/api/v1/cohorts/workspace/assignments/{assignment_id}/submissions/file-ByLearner/{int(current_user.id)}"
    )
    sub = CohortAssignmentSubmission(
        assignment_id=assignment_id,
        learner_user_id=int(current_user.id),
        learner_name=current_user.full_name,
        learner_email=current_user.email,
        status="submitted",
        submission_url=effective_url,
        submission_notes=clean_notes,
        submission_file_name=original_name,
        submission_file_storage_key=stored_key,
        trainer_feedback="Submission received and locked for manual trainer evaluation.",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    if not clean_url and stored_key:
        sub.submission_url = f"/api/v1/cohorts/workspace/assignments/{assignment_id}/submissions/{int(sub.id)}/file"
        db.commit()
        db.refresh(sub)

    return {
        "id": int(sub.id),
        "submission_id": int(sub.id),
        "status": sub.status,
        "submission_url": sub.submission_url,
        "file_name": sub.submission_file_name,
        "submission_file_name": sub.submission_file_name,
    }


@router.get("/assignments/{assignment_id}/submissions/{submission_id}/file")
def download_assignment_submission_file(
    assignment_id: int,
    submission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asg = db.get(CohortAssignment, assignment_id)
    if asg is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    sub = db.get(CohortAssignmentSubmission, submission_id)
    if sub is None or int(sub.assignment_id) != int(assignment_id):
        raise HTTPException(status_code=404, detail="Assignment submission not found")

    role = role_str(current_user)
    if role in _STAFF_ROLES:
        _ensure_teacher_scope_for_item(db, current_user, asg.department_id, asg.cohort_id)
    elif int(sub.learner_user_id) != int(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to download this submission")

    if not sub.submission_file_storage_key:
        raise HTTPException(status_code=404, detail="No uploaded file attached to this submission")

    file_path = os.path.realpath(os.path.join(ASSIGNMENT_SUBMISSIONS_DIR, sub.submission_file_storage_key))
    if not file_path.startswith(os.path.realpath(ASSIGNMENT_SUBMISSIONS_DIR) + os.sep) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Uploaded submission file is missing on server")

    return FileResponse(
        path=file_path,
        filename=sub.submission_file_name or sub.submission_file_storage_key,
        media_type="application/octet-stream",
    )


@router.post("/assignments/{assignment_id}/grade")
def grade_assignment(
    assignment_id: int,
    payload: AssignmentGradeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    asg = db.get(CohortAssignment, assignment_id)
    if asg is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    _ensure_teacher_scope_for_item(db, current_user, asg.department_id, asg.cohort_id)

    stmt = select(CohortAssignmentSubmission).where(CohortAssignmentSubmission.assignment_id == assignment_id)
    if payload.learner_user_id is not None:
        stmt = stmt.where(CohortAssignmentSubmission.learner_user_id == int(payload.learner_user_id))
    else:
        stmt = stmt.order_by(CohortAssignmentSubmission.submitted_at.desc())
    sub = db.scalar(stmt)
    if sub is None:
        raise HTTPException(status_code=404, detail="No learner submission found to grade")

    sub.score = payload.score
    sub.trainer_feedback = payload.feedback.strip()
    sub.status = "graded"
    sub.graded_by_user_id = int(current_user.id)
    sub.graded_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": int(sub.id), "status": sub.status, "score": sub.score}


@router.post("/quizzes", status_code=status.HTTP_201_CREATED)
def create_quiz(
    payload: QuizCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    _ensure_teacher_scope_for_item(db, current_user, payload.department_id, payload.cohort_id)

    dept_name = payload.department_name
    if payload.department_id is not None:
        dept = db.get(Department, int(payload.department_id))
        if dept is not None:
            dept_name = dept.name

    questions = (
        [q.model_dump() for q in payload.questions]
        if payload.questions
        else [
            {
                "id": 1,
                "text": f"Checkpoint question for {payload.title.strip()}?",
                "options": ["Option A (Correct standard)", "Option B", "Option C", "Option D"],
                "correctIndex": 0,
                "explanation": "Demonstrates baseline comprehension of module principles.",
            }
        ]
    )
    qz = CohortQuiz(
        cohort_id=payload.cohort_id,
        department_id=payload.department_id,
        department_name=dept_name or "All / Common",
        title=payload.title.strip(),
        module=payload.module.strip(),
        questions_count=payload.questions_count,
        duration_minutes=payload.duration_minutes,
        due_date=payload.due_date,
        passing_score=payload.passing_score,
        questions_json=json.dumps(questions),
        created_by_user_id=int(current_user.id),
    )
    db.add(qz)
    db.commit()
    db.refresh(qz)
    return {"id": str(qz.id), "backendId": int(qz.id), "title": qz.title}


@router.post("/quizzes/{quiz_id}/submit")
def submit_quiz(
    quiz_id: int,
    payload: QuizSubmitRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    qz = db.get(CohortQuiz, quiz_id)
    if qz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = _parse_json(qz.questions_json, [])
    correct = 0
    for q in questions:
        qid = q.get("id")
        ans = payload.answers.get(qid)
        if ans is None and str(qid) in payload.answers:
            ans = payload.answers[str(qid)]  # type: ignore[index]
        if ans is not None and int(ans) == int(q.get("correctIndex", 0)):
            correct += 1

    total = len(questions) or 1
    score = round((correct / total) * 100)
    passed = score >= int(qz.passing_score)

    sub = db.scalar(
        select(CohortQuizSubmission).where(
            CohortQuizSubmission.quiz_id == quiz_id,
            CohortQuizSubmission.learner_user_id == int(current_user.id),
        )
    )
    if sub is None:
        sub = CohortQuizSubmission(
            quiz_id=quiz_id,
            learner_user_id=int(current_user.id),
            learner_name=current_user.full_name,
            learner_email=current_user.email,
            score=score,
            passed=passed,
            answers_json=json.dumps(payload.answers),
        )
        db.add(sub)
    else:
        sub.score = score
        sub.passed = passed
        sub.answers_json = json.dumps(payload.answers)
        sub.submitted_at = datetime.now(timezone.utc)
    db.commit()
    return {"score": score, "passed": passed}


@router.post("/announcements", status_code=status.HTTP_201_CREATED)
def create_announcement(
    payload: AnnouncementCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    if payload.department_id is not None or payload.cohort_id is not None:
        _ensure_teacher_scope_for_item(db, current_user, payload.department_id, payload.cohort_id)

    ann = CohortAnnouncement(
        cohort_id=payload.cohort_id,
        department_id=payload.department_id,
        title=payload.title.strip(),
        content=payload.content.strip(),
        priority=payload.priority,
        is_pinned=payload.is_pinned,
        tags_json=json.dumps(payload.tags or ["InstructorUpdate"]),
        author_name=f"{current_user.full_name} (Lead Trainer)",
        author_role="Lead Instructor",
        author_avatar=_initials(current_user.full_name),
        created_by_user_id=int(current_user.id),
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)
    return {"id": str(ann.id), "backendId": int(ann.id), "title": ann.title}


@router.delete("/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    ann = db.get(CohortAnnouncement, announcement_id)
    if ann is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    if ann.department_id is not None or ann.cohort_id is not None:
        _ensure_teacher_scope_for_item(db, current_user, ann.department_id, ann.cohort_id)
    db.delete(ann)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/announcements/{announcement_id}/read")
def mark_announcement_read(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ann = db.get(CohortAnnouncement, announcement_id)
    if ann is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    existing = db.scalar(
        select(CohortAnnouncementRead).where(
            CohortAnnouncementRead.announcement_id == announcement_id,
            CohortAnnouncementRead.user_id == int(current_user.id),
        )
    )
    if existing is None:
        db.add(CohortAnnouncementRead(announcement_id=announcement_id, user_id=int(current_user.id)))
        db.commit()
    return {"status": "read"}


@router.post("/discussions", status_code=status.HTTP_201_CREATED)
def create_discussion(
    payload: DiscussionCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = role_str(current_user)
    disc = CohortDiscussion(
        cohort_id=payload.cohort_id,
        department_id=payload.department_id,
        title=payload.title.strip(),
        category=payload.category,
        content=payload.content.strip(),
        author_user_id=int(current_user.id),
        author_name=current_user.full_name,
        author_role="Staff Instructor" if role in _STAFF_ROLES else "Learner",
        author_avatar=_initials(current_user.full_name),
        is_resolved=False,
    )
    db.add(disc)
    db.commit()
    db.refresh(disc)
    return {
        "id": str(disc.id),
        "backendId": int(disc.id),
        "title": disc.title,
        "category": disc.category,
        "author": disc.author_name,
        "authorRole": disc.author_role,
        "authorAvatar": disc.author_avatar,
        "createdAt": _relative_label(disc.created_at),
        "content": disc.content,
        "likes": 0,
        "hasLiked": False,
        "isResolved": False,
        "replies": [],
    }


@router.post("/discussions/{discussion_id}/replies", status_code=status.HTTP_201_CREATED)
def reply_discussion(
    discussion_id: int,
    payload: DiscussionReplyCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    disc = db.get(CohortDiscussion, discussion_id)
    if disc is None:
        raise HTTPException(status_code=404, detail="Discussion not found")
    role = role_str(current_user)
    is_staff = role in _STAFF_ROLES
    rep = CohortDiscussionReply(
        discussion_id=discussion_id,
        author_user_id=int(current_user.id),
        author_name=current_user.full_name,
        author_role="Staff Instructor" if is_staff else "Learner",
        author_avatar=_initials(current_user.full_name),
        content=payload.content.strip(),
        is_trainer_reply=is_staff,
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return {"id": str(rep.id), "author": rep.author_name, "content": rep.content}


@router.post("/discussions/{discussion_id}/like")
def toggle_discussion_like(
    discussion_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    disc = db.get(CohortDiscussion, discussion_id)
    if disc is None:
        raise HTTPException(status_code=404, detail="Discussion not found")
    existing = db.scalar(
        select(CohortDiscussionLike).where(
            CohortDiscussionLike.discussion_id == discussion_id,
            CohortDiscussionLike.user_id == int(current_user.id),
        )
    )
    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(CohortDiscussionLike(discussion_id=discussion_id, user_id=int(current_user.id)))
        liked = True
    db.commit()
    count = len(
        db.scalars(select(CohortDiscussionLike.id).where(CohortDiscussionLike.discussion_id == discussion_id)).all()
    )
    return {"hasLiked": liked, "likes": count}


@router.post("/attendance/toggle")
def toggle_attendance(
    payload: AttendanceToggleRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    existing = db.scalar(
        select(CohortAttendanceEntry).where(
            CohortAttendanceEntry.cohort_id == payload.cohort_id,
            CohortAttendanceEntry.learner_user_id == int(payload.learner_user_id),
            CohortAttendanceEntry.attendance_date == payload.date_str,
        )
    )
    if payload.status:
        next_status = payload.status
    else:
        curr = existing.status if existing else "P"
        next_status = "A" if curr == "P" else ("L" if curr == "A" else "P")

    if existing:
        existing.status = next_status
        existing.recorded_by_user_id = int(current_user.id)
        existing.recorded_by_name = current_user.full_name
    else:
        db.add(
            CohortAttendanceEntry(
                cohort_id=payload.cohort_id,
                learner_user_id=int(payload.learner_user_id),
                attendance_date=payload.date_str,
                status=next_status,
                recorded_by_user_id=int(current_user.id),
                recorded_by_name=current_user.full_name,
            )
        )
    db.commit()
    return {"status": next_status}


@router.post("/attendance/bulk")
def bulk_attendance(
    payload: AttendanceBulkRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_staff(current_user)
    target_ids = payload.learner_user_ids
    if target_ids is None:
        if payload.cohort_id is not None:
            target_ids = [
                int(uid)
                for uid in db.scalars(
                    select(CohortMember.user_id).where(
                        CohortMember.cohort_id == int(payload.cohort_id),
                        CohortMember.status == "active",
                    )
                ).all()
            ]
        else:
            target_ids = [int(u["id"]) for u in _fetch_identity_learners()]

    for lid in target_ids:
        existing = db.scalar(
            select(CohortAttendanceEntry).where(
                CohortAttendanceEntry.cohort_id == payload.cohort_id,
                CohortAttendanceEntry.learner_user_id == int(lid),
                CohortAttendanceEntry.attendance_date == payload.date_str,
            )
        )
        if existing:
            existing.status = payload.status
            existing.recorded_by_user_id = int(current_user.id)
            existing.recorded_by_name = current_user.full_name
        else:
            db.add(
                CohortAttendanceEntry(
                    cohort_id=payload.cohort_id,
                    learner_user_id=int(lid),
                    attendance_date=payload.date_str,
                    status=payload.status,
                    recorded_by_user_id=int(current_user.id),
                    recorded_by_name=current_user.full_name,
                )
            )
    db.commit()
    return {"updated_count": len(target_ids), "status": payload.status}


@router.post("/attendance/check-in")
def check_in_today(
    payload: AttendanceCheckInRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today_iso = date.today().isoformat()
    existing = db.scalar(
        select(CohortAttendanceEntry).where(
            CohortAttendanceEntry.cohort_id == payload.cohort_id,
            CohortAttendanceEntry.learner_user_id == int(current_user.id),
            CohortAttendanceEntry.attendance_date == today_iso,
        )
    )
    if existing:
        existing.status = "P"
        existing.session_title = payload.session_title or existing.session_title or "Daily Session"
        existing.recorded_by_user_id = int(current_user.id)
        existing.recorded_by_name = f"{current_user.full_name} (Self Check-in)"
    else:
        db.add(
            CohortAttendanceEntry(
                cohort_id=payload.cohort_id,
                learner_user_id=int(current_user.id),
                attendance_date=today_iso,
                status="P",
                session_title=payload.session_title or "Daily Session",
                recorded_by_user_id=int(current_user.id),
                recorded_by_name=f"{current_user.full_name} (Self Check-in)",
            )
        )
    db.commit()
    return {"checkedInToday": True, "date": today_iso}


@router.post("/bookmarks/toggle")
def toggle_bookmark(
    payload: BookmarkToggleRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    existing = db.scalar(
        select(CohortMaterialBookmark).where(
            CohortMaterialBookmark.user_id == int(current_user.id),
            CohortMaterialBookmark.material_key == payload.material_key,
        )
    )
    if existing:
        db.delete(existing)
        bookmarked = False
    else:
        db.add(
            CohortMaterialBookmark(
                user_id=int(current_user.id),
                material_key=payload.material_key,
            )
        )
        bookmarked = True
    db.commit()
    return {"isBookmarked": bookmarked}
