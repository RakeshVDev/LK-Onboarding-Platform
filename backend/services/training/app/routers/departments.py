from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from services.training.app.db.session import SessionLocal
from services.training.app.models.entities import Department, StudentDepartmentRequest
from services.training.app.schemas.training import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    StudentDepartmentRequestCreate,
    StudentDepartmentRequestResponse,
    StudentDepartmentRequestReview,
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


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(Permission.MANAGE_DEPARTMENTS)),
):
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    db.delete(department)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete this department while it has dependent records",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
