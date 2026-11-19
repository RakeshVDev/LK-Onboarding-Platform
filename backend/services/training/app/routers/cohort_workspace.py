"""Persistent SQL-backed API endpoints for Cohort Workspace features (replacing browser localStorage)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
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
    CohortMember,
    CohortTeacher,
    Department,
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
                }
                for u in rows
            ]
    except Exception:
        return []


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
        "downloadUrl": les.download_url,
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
            .order_by(CohortLesson.id.asc())
        ).all():
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
                "attachmentUrl": a.attachment_url,
                "attachmentSize": a.attachment_size,
                "submissionDate": _relative_label(display_sub.submitted_at) if display_sub else None,
                "submissionUrl": display_sub.submission_url if display_sub else None,
                "submissionNotes": display_sub.submission_notes if display_sub else None,
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
    elif cohort_id is not None:
        member_ids = [
            int(uid)
            for uid in db.scalars(
                select(CohortMember.user_id).where(
                    CohortMember.cohort_id == int(cohort_id),
                    CohortMember.status == "active",
                )
            ).all()
        ]
        learner_profiles = _fetch_identity_learners(member_ids)
    else:
        learner_profiles = _fetch_identity_learners()

    att_stmt = select(CohortAttendanceEntry)
    if cohort_id is not None:
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

    is_live = payload.type == "live" and bool(payload.is_live_now)
    duration = payload.duration
    if payload.type == "live":
        duration = duration or "2 Hours"
    elif payload.type == "video":
        duration = duration or "15:00"
    else:
        duration = None

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
        is_live_now=is_live,
        trainer_name=payload.trainer or current_user.full_name,
        created_by_user_id=int(current_user.id),
    )
    db.add(les)

    # Also create matching Assignment or Quiz SQL rows when lesson type is assignment/quiz
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
    elif payload.type == "quiz":
        qz = CohortQuiz(
            cohort_id=resolved_cohort_id,
            department_id=resolved_dept_id,
            department_name=dept_name,
            title=payload.title.strip(),
            module=ch.title,
            questions_count=payload.quiz_questions_count or 5,
            duration_minutes=15,
            due_date=payload.scheduled_date or "Upcoming Sprint",
            passing_score=70,
            attachment_name=payload.file_name,
            attachment_url=payload.download_url if payload.download_url and payload.download_url != "#" else None,
            attachment_size=payload.file_size,
            questions_json=json.dumps([
                {
                    "id": 1,
                    "text": f"Core architectural checkpoint for {payload.title.strip()}",
                    "options": [
                        "Option A (Recommended Pattern)",
                        "Option B (Legacy Fallback)",
                        "Option C (Anti-Pattern)",
                        "Option D (Incomplete Spec)",
                    ],
                    "correctIndex": 0,
                    "explanation": "Based on instructor materials and attached assets.",
                }
            ]),
            created_by_user_id=int(current_user.id),
        )
        db.add(qz)

    db.commit()
    db.refresh(les)
    return _serialize_lesson(les)


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
    if sub is None:
        sub = CohortAssignmentSubmission(
            assignment_id=assignment_id,
            learner_user_id=int(current_user.id),
            learner_name=current_user.full_name,
            learner_email=current_user.email,
            status="submitted",
            submission_url=payload.submission_url.strip(),
            submission_notes=payload.submission_notes.strip(),
            trainer_feedback="Submission received successfully and queued for trainer evaluation.",
        )
        db.add(sub)
    else:
        sub.submission_url = payload.submission_url.strip()
        sub.submission_notes = payload.submission_notes.strip()
        sub.status = "submitted"
        sub.submitted_at = datetime.now(timezone.utc)
        sub.trainer_feedback = "Submission received successfully and queued for trainer evaluation."
    db.commit()
    db.refresh(sub)
    return {"id": int(sub.id), "status": sub.status}


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
