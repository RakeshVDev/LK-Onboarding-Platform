
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.identity.app.core.roles import Permission, Role
from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
from services.identity.app.dependencies.auth import (
    get_current_user,
    require_permissions,
)
from services.identity.app.models.user import User as IdentityUser, UserDepartment
from services.training.app.db.session import SessionLocal
from services.training.app.models.entities import (
    Cohort,
    CohortMaterialDelivery,
    CohortMember,
    CohortTeacher,
    Course,
    Department,
    LearningMaterial,
    StudentDepartmentRequest,
)
from services.training.app.routers.assessments import get_learner_allowed_dept_ids
from services.training.app.schemas.cohort import (
    CohortCandidateUser,
    CohortCreate,
    CohortDeliveredMaterialResponse,
    CohortDepartmentCandidatesResponse,
    CohortMemberCreate,
    CohortMemberResponse,
    CohortResponse,
    CohortTeacherInfo,
    CohortTeachersUpdate,
    CohortUpdate,
)
from services.training.app.services.course_sync import (
    MAX_BATCH_TEACHERS,
    ensure_course_for_department,
    ensure_teacher_has_department,
    purge_cohort_records,
)
from services.training.app.services.teacher_scope import (
    get_teacher_assigned_dept_ids,
    is_common_department_id,
    require_teacher_department_access,
    role_str,
)

router = APIRouter(prefix="/cohorts", tags=["Cohorts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_department(db: Session, department_id: int):
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


def get_learner_approved_dept_ids(db: Session, user_id: int) -> set[int] | None:
    """
    Returns allowed department IDs for a learner (All / Common once assessments complete, plus approved department).
    """
    return get_learner_allowed_dept_ids(db, user_id)


def _require_superadmin(current_user, detail: str) -> None:
    if role_str(current_user) != Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def _fetch_identity_users(user_ids: set[int]) -> dict[int, IdentityUser]:
    if not user_ids:
        return {}
    try:
        with IdentitySessionLocal() as id_db:
            rows = id_db.scalars(
                select(IdentityUser).where(IdentityUser.id.in_(list(user_ids)))
            ).all()
            return {int(u.id): u for u in rows}
    except Exception:
        return {}


def _build_cohort_responses(db: Session, cohorts: list[Cohort]) -> list[CohortResponse]:
    if not cohorts:
        return []
    cohort_ids = [int(c.id) for c in cohorts]
    dept_ids = {int(c.department_id) for c in cohorts}
    departments = db.scalars(select(Department).where(Department.id.in_(dept_ids))).all()
    dept_map = {int(d.id): d.name for d in departments}

    ct_rows = db.scalars(
        select(CohortTeacher).where(CohortTeacher.cohort_id.in_(cohort_ids)).order_by(CohortTeacher.id)
    ).all()
    teacher_ids_by_cohort: dict[int, list[int]] = {}
    all_teacher_ids: set[int] = set()
    for row in ct_rows:
        teacher_ids_by_cohort.setdefault(int(row.cohort_id), []).append(int(row.user_id))
        all_teacher_ids.add(int(row.user_id))
    teacher_user_map = _fetch_identity_users(all_teacher_ids)

    member_rows = db.scalars(
        select(CohortMember).where(
            CohortMember.cohort_id.in_(cohort_ids),
            CohortMember.status == "active",
        )
    ).all()
    members_by_cohort: dict[int, list[int]] = {}
    for m in member_rows:
        members_by_cohort.setdefault(int(m.cohort_id), []).append(int(m.user_id))

    deliv_rows = db.execute(
        select(CohortMaterialDelivery.cohort_id, func.count(CohortMaterialDelivery.id))
        .where(CohortMaterialDelivery.cohort_id.in_(cohort_ids))
        .group_by(CohortMaterialDelivery.cohort_id)
    ).all()
    material_count_by_cohort = {int(cid): int(cnt) for cid, cnt in deliv_rows}

    responses: list[CohortResponse] = []
    for c in cohorts:
        t_ids = teacher_ids_by_cohort.get(int(c.id), [])
        teachers = [
            CohortTeacherInfo(
                id=tid,
                full_name=teacher_user_map[tid].full_name if tid in teacher_user_map else f"Teacher #{tid}",
                email=teacher_user_map[tid].email if tid in teacher_user_map else "",
            )
            for tid in t_ids
        ]
        m_ids = members_by_cohort.get(int(c.id), [])
        responses.append(
            CohortResponse(
                id=c.id,
                department_id=c.department_id,
                department_name=dept_map.get(int(c.department_id)),
                course_id=c.course_id,
                name=c.name,
                start_date=c.start_date,
                end_date=c.end_date,
                status=c.status,
                teacher_ids=t_ids,
                teachers=teachers,
                member_ids=m_ids,
                learner_count=len(m_ids),
                material_count=material_count_by_cohort.get(int(c.id), 0),
            )
        )
    return responses


@router.get("/department-candidates", response_model=CohortDepartmentCandidatesResponse)
def get_department_batch_candidates(
    department_id: int = Query(gt=0),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_superadmin(current_user, "Only SuperAdmin can create batches or load department candidates.")
    dept = validate_department(db, department_id)
    if is_common_department_id(db, dept.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batches must be created for a concrete department rather than All / Common.",
        )

    approved_req_user_ids = set(
        db.scalars(
            select(StudentDepartmentRequest.user_id).where(
                StudentDepartmentRequest.department_id == dept.id,
                StudentDepartmentRequest.status == "approved",
            )
        ).all()
    )

    learners: list[CohortCandidateUser] = []
    teachers: list[CohortCandidateUser] = []
    with IdentitySessionLocal() as id_db:
        learner_rows = id_db.scalars(
            select(IdentityUser)
            .where(
                IdentityUser.role == Role.LEARNER.value,
                IdentityUser.is_active == True,  # noqa: E712
            )
            .order_by(IdentityUser.full_name.asc())
        ).all()
        for u in learner_rows:
            matches_identity = (
                bool(u.department_approved)
                and str(u.selected_department_id or "").strip() == str(int(dept.id))
            )
            if matches_identity or int(u.id) in approved_req_user_ids:
                learners.append(
                    CohortCandidateUser(id=int(u.id), full_name=u.full_name, email=u.email)
                )

        teacher_rows = id_db.scalars(
            select(IdentityUser)
            .where(
                IdentityUser.role == Role.TEACHER.value,
                IdentityUser.is_active == True,  # noqa: E712
            )
            .order_by(IdentityUser.full_name.asc())
        ).all()
        t_dept_rows = id_db.scalars(select(UserDepartment)).all()
        depts_by_user: dict[int, list[int]] = {}
        for row in t_dept_rows:
            depts_by_user.setdefault(int(row.user_id), []).append(int(row.department_id))
        for t in teacher_rows:
            teachers.append(
                CohortCandidateUser(
                    id=int(t.id),
                    full_name=t.full_name,
                    email=t.email,
                    assigned_department_ids=sorted(set(depts_by_user.get(int(t.id), []))),
                )
            )

    return CohortDepartmentCandidatesResponse(
        department_id=int(dept.id),
        learners=learners,
        teachers=teachers,
    )


@router.post("", response_model=CohortResponse, status_code=status.HTTP_201_CREATED)
def create_cohort(
    payload: CohortCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_superadmin(current_user, "Only SuperAdmin can create a new batch/cohort.")
    dept = validate_department(db, payload.department_id)
    if not dept.is_active:
        raise HTTPException(status_code=400, detail="Cannot create a batch for an inactive department.")
    if is_common_department_id(db, dept.id):
        raise HTTPException(
            status_code=400,
            detail="Batches must be created for a concrete department (not All / Common).",
        )

    if (
        payload.start_date
        and payload.end_date
        and payload.end_date < payload.start_date
    ):
        raise HTTPException(
            status_code=422,
            detail="end_date must be on or after start_date",
        )

    clean_teacher_ids = list(dict.fromkeys(int(tid) for tid in payload.teacher_ids if int(tid) > 0))
    if len(clean_teacher_ids) < 1 or len(clean_teacher_ids) > MAX_BATCH_TEACHERS:
        raise HTTPException(
            status_code=422,
            detail=f"A batch must be assigned between 1 and {MAX_BATCH_TEACHERS} teachers.",
        )

    duplicate = db.scalar(
        select(Cohort).where(
            Cohort.department_id == payload.department_id,
            Cohort.name == payload.name,
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="A cohort with this name already exists in the department",
        )

    # Assigning a teacher to a batch automatically assigns that department to the teacher (up to 8)
    for tid in clean_teacher_ids:
        ensure_teacher_has_department(
            db,
            tid,
            dept.id,
            int(current_user.id),
            identity_session_factory=IdentitySessionLocal,
        )

    course = ensure_course_for_department(db, dept, seed_common_if_new=True)
    cohort = Cohort(
        department_id=dept.id,
        course_id=course.id,
        name=payload.name.strip(),
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status or "active",
    )
    db.add(cohort)
    db.flush()

    for tid in clean_teacher_ids:
        db.add(
            CohortTeacher(
                cohort_id=cohort.id,
                user_id=tid,
                assigned_by_user_id=int(current_user.id),
            )
        )

    # Auto-add all active learners of that department (minus excluded_learner_ids)
    excluded_ids = {int(uid) for uid in payload.excluded_learner_ids}
    approved_req_ids = set(
        db.scalars(
            select(StudentDepartmentRequest.user_id).where(
                StudentDepartmentRequest.department_id == dept.id,
                StudentDepartmentRequest.status == "approved",
            )
        ).all()
    )
    enrolled_ids: list[int] = []
    with IdentitySessionLocal() as id_db:
        active_learners = id_db.scalars(
            select(IdentityUser).where(
                IdentityUser.role == Role.LEARNER.value,
                IdentityUser.is_active == True,  # noqa: E712
            )
        ).all()
        for learner in active_learners:
            matches_identity = (
                bool(learner.department_approved)
                and str(learner.selected_department_id or "").strip() == str(int(dept.id))
            )
            if (matches_identity or int(learner.id) in approved_req_ids) and int(learner.id) not in excluded_ids:
                enrolled_ids.append(int(learner.id))

    for lid in enrolled_ids:
        db.add(CohortMember(cohort_id=cohort.id, user_id=lid, status="active"))

    db.commit()
    db.refresh(cohort)
    return _build_cohort_responses(db, [cohort])[0]


@router.get("", response_model=list[CohortResponse])
def list_cohorts(
    department_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Cohort).where(Cohort.status != "completed").order_by(Cohort.id)
    role = role_str(current_user)

    if role == Role.LEARNER.value:
        allowed_dept_ids = get_learner_approved_dept_ids(db, current_user.id)
        if not allowed_dept_ids:
            return []
        member_cohort_ids = list(
            db.scalars(
                select(CohortMember.cohort_id).where(
                    CohortMember.user_id == int(current_user.id),
                    CohortMember.status == "active",
                )
            ).all()
        )
        if not member_cohort_ids:
            return []
        query = query.where(
            Cohort.department_id.in_(allowed_dept_ids),
            Cohort.id.in_(member_cohort_ids),
        )
    elif role == Role.TEACHER.value:
        allowed_teacher_depts = get_teacher_assigned_dept_ids(
            db, int(current_user.id), identity_session_factory=IdentitySessionLocal
        )
        if not allowed_teacher_depts:
            return []
        if department_id is not None:
            if int(department_id) not in allowed_teacher_depts:
                return []
            query = query.where(Cohort.department_id == department_id)
        else:
            query = query.where(Cohort.department_id.in_(allowed_teacher_depts))

        cohorts_in_depts = db.scalars(query).all()
        if not cohorts_in_depts:
            return []
        c_ids = [int(c.id) for c in cohorts_in_depts]
        ct_rows = db.scalars(select(CohortTeacher).where(CohortTeacher.cohort_id.in_(c_ids))).all()
        assigned_teachers_map: dict[int, set[int]] = {}
        for row in ct_rows:
            assigned_teachers_map.setdefault(int(row.cohort_id), set()).add(int(row.user_id))
        visible_cohorts = [
            c
            for c in cohorts_in_depts
            if (int(c.id) not in assigned_teachers_map)
            or (int(current_user.id) in assigned_teachers_map[int(c.id)])
        ]
        return _build_cohort_responses(db, visible_cohorts)
    elif department_id is not None:
        query = query.where(Cohort.department_id == department_id)

    cohorts = db.scalars(query).all()
    return _build_cohort_responses(db, cohorts)


@router.get("/{cohort_id}", response_model=CohortResponse)
def get_cohort(
    cohort_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cohort = db.get(Cohort, cohort_id)
    if not cohort or (cohort.status or "").lower() == "completed":
        raise HTTPException(status_code=404, detail="Cohort not found")

    if role_str(current_user) == Role.LEARNER.value:
        allowed_dept_ids = get_learner_approved_dept_ids(db, current_user.id)
        if not allowed_dept_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your department allocation is pending instructor/admin approval. Cohorts will unlock once approved.",
            )
        if cohort.department_id not in allowed_dept_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to cohorts outside your approved department.",
            )
        is_member = db.scalar(
            select(CohortMember).where(
                CohortMember.cohort_id == cohort_id,
                CohortMember.user_id == int(current_user.id),
                CohortMember.status == "active",
            )
        )
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not an active member of this batch.",
            )
    else:
        require_teacher_department_access(
            db, current_user, cohort.department_id, identity_session_factory=IdentitySessionLocal
        )

    return _build_cohort_responses(db, [cohort])[0]


@router.patch("/{cohort_id}", response_model=CohortResponse)
def update_cohort(
    cohort_id: int,
    payload: CohortUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permissions(Permission.MANAGE_COHORTS)
    ),
):
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    require_teacher_department_access(db, current_user, cohort.department_id)
    changes = payload.model_dump(exclude_unset=True)

    if changes.get("department_id") is not None:
        require_teacher_department_access(db, current_user, changes["department_id"])
        validate_department(db, changes["department_id"])

    new_start = changes.get("start_date", cohort.start_date)
    new_end = changes.get("end_date", cohort.end_date)
    if new_start and new_end and new_end < new_start:
        raise HTTPException(
            status_code=422,
            detail="end_date must be on or after start_date",
        )

    new_department_id = changes.get("department_id", cohort.department_id)
    new_name = changes.get("name", cohort.name)
    duplicate = db.scalar(
        select(Cohort).where(
            Cohort.department_id == new_department_id,
            Cohort.name == new_name,
            Cohort.id != cohort_id,
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="A cohort with this name already exists in the department",
        )

    for field, value in changes.items():
        if field == "status" and str(value).lower() == "completed":
            _require_superadmin(current_user, "Only SuperAdmin can end a batch.")
        setattr(cohort, field, value)

    db.commit()
    db.refresh(cohort)
    return _build_cohort_responses(db, [cohort])[0]


@router.put("/{cohort_id}/teachers", response_model=CohortResponse)
def update_cohort_teachers(
    cohort_id: int,
    payload: CohortTeachersUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_superadmin(current_user, "Only SuperAdmin can assign teachers to a batch.")
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    clean_teacher_ids = list(dict.fromkeys(int(tid) for tid in payload.teacher_ids if int(tid) > 0))
    if len(clean_teacher_ids) < 1 or len(clean_teacher_ids) > MAX_BATCH_TEACHERS:
        raise HTTPException(
            status_code=422,
            detail=f"A batch must be assigned between 1 and {MAX_BATCH_TEACHERS} teachers.",
        )

    for tid in clean_teacher_ids:
        ensure_teacher_has_department(
            db,
            tid,
            cohort.department_id,
            int(current_user.id),
            identity_session_factory=IdentitySessionLocal,
        )

    db.execute(delete(CohortTeacher).where(CohortTeacher.cohort_id == cohort_id))
    for tid in clean_teacher_ids:
        db.add(
            CohortTeacher(
                cohort_id=cohort_id,
                user_id=tid,
                assigned_by_user_id=int(current_user.id),
            )
        )
    db.commit()
    db.refresh(cohort)
    return _build_cohort_responses(db, [cohort])[0]


@router.post("/{cohort_id}/end", response_model=dict)
def end_cohort(
    cohort_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_superadmin(current_user, "Only SuperAdmin can end a batch/cohort.")
    cohort = purge_cohort_records(db, cohort_id, delete_cohort_row=True)
    return {
        "status": "deleted",
        "cohort_id": cohort_id,
        "name": cohort.name,
        "message": "Batch ended and all cohort records/deliveries purged. Course Permanent Vault preserved.",
    }


@router.get(
    "/{cohort_id}/materials",
    response_model=list[CohortDeliveredMaterialResponse],
)
def list_cohort_delivered_materials(
    cohort_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cohort = db.get(Cohort, cohort_id)
    if not cohort or (cohort.status or "").lower() == "completed":
        raise HTTPException(status_code=404, detail="Cohort not found")

    role = role_str(current_user)
    if role == Role.LEARNER.value:
        allowed_dept_ids = get_learner_approved_dept_ids(db, int(current_user.id))
        if not allowed_dept_ids or cohort.department_id not in allowed_dept_ids:
            raise HTTPException(status_code=403, detail="Department access denied")
        is_member = db.scalar(
            select(CohortMember).where(
                CohortMember.cohort_id == cohort_id,
                CohortMember.user_id == int(current_user.id),
                CohortMember.status == "active",
            )
        )
        if not is_member:
            raise HTTPException(status_code=403, detail="You are not an active member of this batch.")
    elif role == Role.TEACHER.value:
        require_teacher_department_access(
            db, current_user, cohort.department_id, identity_session_factory=IdentitySessionLocal
        )

    rows = db.execute(
        select(CohortMaterialDelivery, LearningMaterial, Course, Department)
        .join(LearningMaterial, LearningMaterial.id == CohortMaterialDelivery.material_id)
        .join(Course, Course.id == CohortMaterialDelivery.course_id)
        .join(Department, Department.id == Course.department_id)
        .where(
            CohortMaterialDelivery.cohort_id == cohort_id,
            LearningMaterial.is_active == True,  # noqa: E712
        )
        .order_by(CohortMaterialDelivery.sent_at.desc(), CohortMaterialDelivery.id.desc())
    ).all()

    sender_ids = {int(deliv.sent_by_user_id) for deliv, _, _, _ in rows}
    sender_map = _fetch_identity_users(sender_ids)
    return [
        CohortDeliveredMaterialResponse(
            id=deliv.id,
            cohort_id=deliv.cohort_id,
            course_id=deliv.course_id,
            material_id=mat.id,
            title=mat.title,
            material_type=mat.material_type,
            storage_key=mat.storage_key,
            source_department_name=dept.name,
            sent_by_user_id=deliv.sent_by_user_id,
            sent_by_name=(
                sender_map[int(deliv.sent_by_user_id)].full_name
                if int(deliv.sent_by_user_id) in sender_map
                else None
            ),
            sent_at=deliv.sent_at,
        )
        for deliv, mat, _, dept in rows
    ]


@router.delete("/{cohort_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cohort(
    cohort_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    _require_superadmin(current_user, "Only SuperAdmin can delete or end a batch/cohort.")
    purge_cohort_records(db, cohort_id, delete_cohort_row=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------
# Cohort Members Management
# --------------------------------------------------

@router.get(
    "/{cohort_id}/members",
    response_model=list[CohortMemberResponse],
)
def list_cohort_members(
    cohort_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    if current_user.role == Role.LEARNER:
        allowed_dept_ids = get_learner_approved_dept_ids(db, current_user.id)
        if not allowed_dept_ids or cohort.department_id not in allowed_dept_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view members of this cohort",
            )
    else:
        require_teacher_department_access(db, current_user, cohort.department_id)

    return db.scalars(
        select(CohortMember)
        .where(CohortMember.cohort_id == cohort_id)
        .order_by(CohortMember.id.desc())
    ).all()


@router.post(
    "/{cohort_id}/members",
    response_model=CohortMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_cohort_member(
    cohort_id: int,
    payload: CohortMemberCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permissions(Permission.MANAGE_COHORTS)
    ),
):
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    require_teacher_department_access(db, current_user, cohort.department_id)
    existing = db.scalar(
        select(CohortMember).where(
            CohortMember.cohort_id == cohort_id,
            CohortMember.user_id == payload.user_id,
        )
    )
    if existing:
        existing.status = payload.status
        db.commit()
        db.refresh(existing)
        return existing

    member = CohortMember(
        cohort_id=cohort_id,
        user_id=payload.user_id,
        status=payload.status,
    )
    db.add(member)
    try:
        db.commit()
        db.refresh(member)
        return member
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not add member to cohort")


@router.delete(
    "/{cohort_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_cohort_member(
    cohort_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permissions(Permission.MANAGE_COHORTS)
    ),
):
    cohort = db.get(Cohort, cohort_id)
    if cohort:
        require_teacher_department_access(db, current_user, cohort.department_id)

    member = db.scalar(
        select(CohortMember).where(
            CohortMember.cohort_id == cohort_id,
            CohortMember.user_id == user_id,
        )
    )
    if not member:
        raise HTTPException(status_code=404, detail="Cohort member record not found")

    db.delete(member)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

