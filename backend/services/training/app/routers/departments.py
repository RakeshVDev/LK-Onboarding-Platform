from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from services.training.app.db.session import SessionLocal
from services.training.app.models.entities import Department, StudentDepartmentRequest
from services.training.app.schemas.training import (
    CourseDeletionActionResponse,
    DeletionRequestResponse,
    DepartmentCreate,
    DepartmentMemberItem,
    DepartmentMembersResponse,
    DepartmentResponse,
    DepartmentUpdate,
    StudentDepartmentRequestCreate,
    StudentDepartmentRequestResponse,
    StudentDepartmentRequestReview,
)
from services.training.app.services.course_sync import (
    ensure_course_for_department,
    get_active_superadmin_users,
    initiate_or_approve_deletion,
    serialize_deletion_request,
)

from services.identity.app.core.roles import Permission, Role
from services.identity.app.dependencies.auth import (
    get_current_user,
    require_permissions,
)
from services.identity.app.db.session import SessionLocal as IdentitySessionLocal
from services.identity.app.models.user import User as IdentityUser
from services.training.app.routers.assessments import compute_learner_assessment_status
from services.training.app.services.teacher_scope import (
    get_teacher_assigned_dept_ids,
    require_teacher_department_access,
    role_str,
)

router = APIRouter(prefix="/departments", tags=["Departments"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_users_map(user_ids: set[int]) -> dict[int, dict[str, str]]:
    if not user_ids:
        return {}
    try:
        with IdentitySessionLocal() as id_db:
            users = id_db.scalars(
                select(IdentityUser).where(IdentityUser.id.in_(user_ids))
            ).all()
            return {
                u.id: {"full_name": u.full_name, "email": u.email}
                for u in users
            }
    except Exception:
        return {}


def build_request_response(
    req: StudentDepartmentRequest,
    dept: Department | None,
    users_map: dict[int, dict[str, str]],
    approved_req: StudentDepartmentRequest | None = None,
    approved_dept: Department | None = None,
) -> StudentDepartmentRequestResponse:
    user_info = users_map.get(req.user_id, {})
    reviewer_info = users_map.get(req.reviewed_by_user_id, {}) if req.reviewed_by_user_id else {}

    current_approved_id = None
    current_approved_name = None
    is_change_request = False
    if approved_req and req.status == "pending" and approved_req.id != req.id:
        is_change_request = True
        current_approved_id = approved_req.department_id
        if approved_dept:
            current_approved_name = approved_dept.name

    return StudentDepartmentRequestResponse(
        id=req.id,
        user_id=req.user_id,
        user_name=user_info.get("full_name"),
        user_email=user_info.get("email"),
        department_id=req.department_id,
        department_name=dept.name if dept else None,
        status=req.status,
        notes=req.notes,
        reviewed_by_user_id=req.reviewed_by_user_id,
        reviewed_by_name=reviewer_info.get("full_name"),
        reviewed_at=req.reviewed_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
        current_approved_department_id=current_approved_id,
        current_approved_department_name=current_approved_name,
        is_change_request=is_change_request,
    )


# ----------------------------------------------------
# Student Department Allocation Requests Endpoints
# ----------------------------------------------------

@router.post(
    "/my-request",
    response_model=StudentDepartmentRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_my_department_request(
    payload: StudentDepartmentRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    department = db.get(Department, payload.department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    if not department.is_active:
        raise HTTPException(status_code=400, detail="This department is not currently active")
    if department.name.strip().lower() in {"all / common", "all/common", "common"}:
        raise HTTPException(
            status_code=400,
            detail="Please choose a specialization department rather than All / Common",
        )

    # Check if learner already has an approved allocation in this SAME department
    existing_approved = db.scalar(
        select(StudentDepartmentRequest).where(
            StudentDepartmentRequest.user_id == current_user.id,
            StudentDepartmentRequest.status == "approved",
        )
    )
    if current_user.role == Role.LEARNER:
        with IdentitySessionLocal() as idb:
            id_user = idb.get(IdentityUser, current_user.id)
            if id_user is not None:
                if not bool(id_user.all_assessments_completed):
                    assessment_status = compute_learner_assessment_status(db, current_user.id)
                    if not (assessment_status.all_completed and assessment_status.total_assigned > 0):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Complete all assigned assessments before choosing a department.",
                        )
                    id_user.all_assessments_completed = True
                    idb.commit()
                if not bool(id_user.is_activated_by_admin):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Your account must be activated by an administrator before choosing a department.",
                    )
                if bool(id_user.department_approved):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Your department selection is already approved.",
                    )
            else:
                if not existing_approved:
                    assessment_status = compute_learner_assessment_status(db, current_user.id)
                    if not assessment_status.all_completed:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=(
                                f"Complete all assigned assessments ({assessment_status.completed_count}/"
                                f"{assessment_status.total_assigned}) before choosing a department."
                            ),
                        )
    if existing_approved and existing_approved.department_id == payload.department_id:
        raise HTTPException(
            status_code=400,
            detail=f"You already have an approved allocation in the {department.name} department.",
        )

    approved_dept = None
    if existing_approved:
        approved_dept = db.get(Department, existing_approved.department_id)

    # Check if there is an existing pending request
    req = db.scalar(
        select(StudentDepartmentRequest).where(
            StudentDepartmentRequest.user_id == current_user.id,
            StudentDepartmentRequest.status == "pending",
        )
    )
    if req:
        req.department_id = payload.department_id
        if payload.notes is not None:
            req.notes = payload.notes
        req.updated_at = datetime.now(timezone.utc)
    else:
        req = StudentDepartmentRequest(
            user_id=current_user.id,
            department_id=payload.department_id,
            notes=payload.notes,
            status="pending",
        )
        db.add(req)

    db.commit()
    db.refresh(req)

    try:
        with IdentitySessionLocal() as idb:
            id_user = idb.get(IdentityUser, current_user.id)
            if id_user is not None:
                id_user.selected_department_id = str(department.id)
                idb.commit()
    except Exception as exc:
        print(f"  [Onboarding Sync] Unable to persist selected_department_id for user {current_user.id}: {exc}")

    users_map = get_users_map({current_user.id})
    return build_request_response(
        req, department, users_map, approved_req=existing_approved, approved_dept=approved_dept
    )


@router.get("/my-request", response_model=StudentDepartmentRequestResponse | None)
def get_my_department_request(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Check for pending request first (could be an initial request or a change request)
    pending_req = db.scalar(
        select(StudentDepartmentRequest).where(
            StudentDepartmentRequest.user_id == current_user.id,
            StudentDepartmentRequest.status == "pending",
        ).order_by(StudentDepartmentRequest.id.desc())
    )
    approved_req = db.scalar(
        select(StudentDepartmentRequest).where(
            StudentDepartmentRequest.user_id == current_user.id,
            StudentDepartmentRequest.status == "approved",
        ).order_by(StudentDepartmentRequest.id.desc())
    )

    if pending_req:
        dept = db.get(Department, pending_req.department_id)
        approved_dept = db.get(Department, approved_req.department_id) if approved_req else None
        reviewer_ids = {pending_req.reviewed_by_user_id} if pending_req.reviewed_by_user_id else set()
        users_map = get_users_map({current_user.id} | reviewer_ids)
        return build_request_response(
            pending_req, dept, users_map, approved_req=approved_req, approved_dept=approved_dept
        )

    if approved_req:
        dept = db.get(Department, approved_req.department_id)
        reviewer_ids = {approved_req.reviewed_by_user_id} if approved_req.reviewed_by_user_id else set()
        users_map = get_users_map({current_user.id} | reviewer_ids)
        return build_request_response(approved_req, dept, users_map)

    # If neither, return latest request (e.g. rejected or superseded)
    latest_req = db.scalar(
        select(StudentDepartmentRequest).where(
            StudentDepartmentRequest.user_id == current_user.id,
        ).order_by(StudentDepartmentRequest.id.desc())
    )
    if not latest_req:
        return None

    dept = db.get(Department, latest_req.department_id)
    reviewer_ids = {latest_req.reviewed_by_user_id} if latest_req.reviewed_by_user_id else set()
    users_map = get_users_map({current_user.id} | reviewer_ids)
    return build_request_response(latest_req, dept, users_map)


@router.get("/requests", response_model=list[StudentDepartmentRequestResponse])
def list_department_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in [Role.SUPERADMIN, Role.ADMIN, Role.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and administrators can review department allocation requests",
        )

    query = select(StudentDepartmentRequest).order_by(
        StudentDepartmentRequest.created_at.desc()
    )
    if role_str(current_user) == Role.TEACHER.value:
        allowed_dept_ids = get_teacher_assigned_dept_ids(db, int(current_user.id))
        if not allowed_dept_ids:
            return []
        query = query.where(StudentDepartmentRequest.department_id.in_(allowed_dept_ids))
    if status_filter:
        query = query.where(StudentDepartmentRequest.status == status_filter)

    requests = db.scalars(query).all()
    if not requests:
        return []

    dept_ids = {r.department_id for r in requests}
    departments = db.scalars(
        select(Department).where(Department.id.in_(dept_ids))
    ).all()
    dept_map = {d.id: d for d in departments}

    user_ids = {r.user_id for r in requests}
    reviewer_ids = {r.reviewed_by_user_id for r in requests if r.reviewed_by_user_id}
    users_map = get_users_map(user_ids | reviewer_ids)

    return [
        build_request_response(r, dept_map.get(r.department_id), users_map)
        for r in requests
    ]


@router.post(
    "/requests/{request_id}/review",
    response_model=StudentDepartmentRequestResponse,
)
def review_department_request(
    request_id: int,
    payload: StudentDepartmentRequestReview,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in [Role.SUPERADMIN, Role.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can approve or reject department allocation requests",
        )

    req = db.get(StudentDepartmentRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    target_dept_id = payload.department_id or req.department_id
    dept = db.get(Department, target_dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    if payload.status == "approved":
        with IdentitySessionLocal() as idb:
            id_user = idb.get(IdentityUser, req.user_id)
            if id_user is not None and id_user.role == Role.LEARNER.value:
                if not bool(id_user.all_assessments_completed) or not bool(id_user.is_activated_by_admin):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Learner must complete assessments and be activated by an admin before department approval",
                    )

        req.department_id = target_dept_id
        # Mark other requests of the same learner as superseded
        db.execute(
            update(StudentDepartmentRequest)
            .where(
                StudentDepartmentRequest.user_id == req.user_id,
                StudentDepartmentRequest.id != req.id,
                StudentDepartmentRequest.status != "rejected",
            )
            .values(status="superseded")
        )

    req.status = payload.status
    req.reviewed_by_user_id = current_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    if payload.notes:
        req.notes = payload.notes

    db.commit()
    db.refresh(req)

    try:
        with IdentitySessionLocal() as idb:
            id_user = idb.get(IdentityUser, req.user_id)
            if id_user is not None:
                if payload.status == "approved":
                    id_user.selected_department_id = str(dept.id)
                    id_user.department_approved = True
                elif payload.status == "rejected":
                    id_user.selected_department_id = None
                    id_user.department_approved = False
                idb.commit()
    except Exception as exc:
        print(f"  [Onboarding Sync] Unable to update identity department approval for user {req.user_id}: {exc}")

    users_map = get_users_map({req.user_id, current_user.id})
    return build_request_response(req, dept, users_map)


# ----------------------------------------------------
# Standard Department CRUD Endpoints
# ----------------------------------------------------

@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(Permission.MANAGE_DEPARTMENTS)),
):
    existing = db.scalar(
        select(Department).where(Department.name == payload.name)
    )
    if existing:
        raise HTTPException(status_code=409, detail="Department name already exists")

    department = Department(**payload.model_dump())
    db.add(department)
    db.flush()
    ensure_course_for_department(db, department, seed_common_if_new=True)
    db.commit()
    db.refresh(department)
    return department


@router.get("", response_model=list[DepartmentResponse])
def list_departments(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Department).order_by(Department.id)
    if role_str(current_user) == Role.TEACHER.value:
        allowed = get_teacher_assigned_dept_ids(db, int(current_user.id))
        if not allowed:
            return []
        query = query.where(Department.id.in_(allowed))
    return db.scalars(query).all()


@router.get("/deletion-requests", response_model=list[DeletionRequestResponse])
def list_deletion_requests(
    status_filter: Annotated[str | None, Query(alias="status")] = "pending",
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_str(current_user) != Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin can view course/department deletion approval requests.",
        )
    from services.training.app.models.entities import DepartmentCourseDeletionRequest

    stmt = select(DepartmentCourseDeletionRequest).order_by(DepartmentCourseDeletionRequest.id.desc())
    if status_filter:
        stmt = stmt.where(DepartmentCourseDeletionRequest.status == status_filter)
    rows = db.scalars(stmt).all()
    superadmins = get_active_superadmin_users(identity_session_factory=IdentitySessionLocal)
    return [DeletionRequestResponse(**serialize_deletion_request(r, superadmins)) for r in rows]


@router.post(
    "/deletion-requests/{request_id}/approve",
    response_model=CourseDeletionActionResponse,
)
def approve_deletion_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_str(current_user) != Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin can approve course/department deletion.",
        )
    from services.training.app.models.entities import Course, DepartmentCourseDeletionRequest

    req = db.get(DepartmentCourseDeletionRequest, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deletion request not found")
    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deletion request is already {req.status}",
        )
    dept = db.get(Department, req.department_id)
    if dept is None:
        req.status = "executed"
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department already deleted")
    paired_course = db.scalars(select(Course).where(Course.department_id == dept.id)).first()
    deleted, req_data = initiate_or_approve_deletion(
        db,
        department=dept,
        target_type=req.target_type,
        course_id=paired_course.id if paired_course else req.course_id,
        current_user_id=int(current_user.id),
        identity_session_factory=IdentitySessionLocal,
    )
    msg = (
        f"Unanimous SuperAdmin approval reached. Deleted '{dept.name}' and its paired Course."
        if deleted
        else f"Approval recorded ({req_data['approved_count']}/{req_data['required_count']} SuperAdmins)."
    )
    return CourseDeletionActionResponse(
        status="deleted" if deleted else "pending_approval",
        department_id=req_data["department_id"],
        course_id=req_data["course_id"],
        message=msg,
        request=DeletionRequestResponse(**req_data),
    )


@router.post(
    "/deletion-requests/{request_id}/reject",
    response_model=DeletionRequestResponse,
)
def reject_deletion_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_str(current_user) != Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin can reject course/department deletion.",
        )
    from services.training.app.models.entities import DepartmentCourseDeletionRequest

    req = db.get(DepartmentCourseDeletionRequest, request_id)
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deletion request not found")
    if req.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Deletion request is already {req.status}",
        )
    req.status = "rejected"
    db.commit()
    db.refresh(req)
    superadmins = get_active_superadmin_users(identity_session_factory=IdentitySessionLocal)
    return DeletionRequestResponse(**serialize_deletion_request(req, superadmins))


@router.get("/{department_id}/members", response_model=DepartmentMembersResponse)
def get_department_members(
    department_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    caller_role = role_str(current_user)
    if caller_role not in {Role.SUPERADMIN.value, Role.ADMIN.value, Role.TEACHER.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin, Admin, and assigned Teachers can view department members.",
        )

    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    if caller_role == Role.TEACHER.value:
        require_teacher_department_access(db, current_user, department.id)

    approved_req_user_ids = {
        int(uid)
        for uid in db.scalars(
            select(StudentDepartmentRequest.user_id).where(
                StudentDepartmentRequest.department_id == department.id,
                StudentDepartmentRequest.status == "approved",
            )
        ).all()
        if uid is not None
    }

    teachers: list[DepartmentMemberItem] = []
    students_map: dict[int, DepartmentMemberItem] = {}

    try:
        from services.identity.app.models.user import UserDepartment

        with IdentitySessionLocal() as id_db:
            if caller_role in {Role.SUPERADMIN.value, Role.ADMIN.value}:
                teacher_rows = id_db.scalars(
                    select(IdentityUser)
                    .join(UserDepartment, UserDepartment.user_id == IdentityUser.id)
                    .where(
                        UserDepartment.department_id == department.id,
                        IdentityUser.role == Role.TEACHER.value,
                        IdentityUser.is_active == True,  # noqa: E712
                    )
                    .order_by(IdentityUser.full_name.asc())
                ).all()
                teachers = [
                    DepartmentMemberItem(
                        id=int(u.id),
                        full_name=u.full_name,
                        email=u.email,
                        role=str(u.role),
                        is_active=bool(u.is_active),
                    )
                    for u in teacher_rows
                ]

            dept_str = str(department.id)
            direct_students = id_db.scalars(
                select(IdentityUser)
                .where(
                    IdentityUser.role == Role.LEARNER.value,
                    IdentityUser.is_active == True,  # noqa: E712
                    IdentityUser.selected_department_id == dept_str,
                    IdentityUser.department_approved == True,  # noqa: E712
                )
                .order_by(IdentityUser.full_name.asc())
            ).all()
            for u in direct_students:
                students_map[int(u.id)] = DepartmentMemberItem(
                    id=int(u.id),
                    full_name=u.full_name,
                    email=u.email,
                    role=str(u.role),
                    is_active=bool(u.is_active),
                )

            missing_req_ids = approved_req_user_ids - set(students_map.keys())
            if missing_req_ids:
                extra_students = id_db.scalars(
                    select(IdentityUser)
                    .where(
                        IdentityUser.id.in_(missing_req_ids),
                        IdentityUser.role == Role.LEARNER.value,
                        IdentityUser.is_active == True,  # noqa: E712
                    )
                ).all()
                for u in extra_students:
                    students_map[int(u.id)] = DepartmentMemberItem(
                        id=int(u.id),
                        full_name=u.full_name,
                        email=u.email,
                        role=str(u.role),
                        is_active=bool(u.is_active),
                    )
    except Exception:
        pass

    students = sorted(students_map.values(), key=lambda s: s.full_name.lower())
    return DepartmentMembersResponse(
        department_id=department.id,
        department_name=department.name,
        teachers=teachers,
        students=students,
    )


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    require_teacher_department_access(db, current_user, department.id)
    return department


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(Permission.MANAGE_DEPARTMENTS)),
):
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        duplicate = db.scalar(
            select(Department).where(
                Department.name == changes["name"],
                Department.id != department_id,
            )
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Department name already exists",
            )

    for field, value in changes.items():
        setattr(department, field, value)

    db.commit()
    db.refresh(department)
    return department


@router.delete("/{department_id}", response_model=CourseDeletionActionResponse)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_str(current_user) != Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin can delete a department or course.",
        )

    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import JSONResponse
    from services.training.app.models.entities import Course

    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    paired_course = db.scalars(select(Course).where(Course.department_id == department_id)).first()
    deleted, req_data = initiate_or_approve_deletion(
        db,
        department=department,
        target_type="department",
        course_id=paired_course.id if paired_course else None,
        current_user_id=int(current_user.id),
        identity_session_factory=IdentitySessionLocal,
    )
    body = CourseDeletionActionResponse(
        status="deleted" if deleted else "pending_approval",
        department_id=req_data["department_id"],
        course_id=req_data["course_id"],
        message=(
            f"Deleted department '{req_data['department_name']}' and its paired Course."
            if deleted
            else (
                f"Deletion request generated ({req_data['approved_count']}/{req_data['required_count']} "
                "SuperAdmins approved). Waiting for all remaining SuperAdmins to approve."
            )
        ),
        request=DeletionRequestResponse(**req_data),
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK if deleted else status.HTTP_202_ACCEPTED,
        content=jsonable_encoder(body),
    )
