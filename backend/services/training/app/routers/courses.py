
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
from services.training.app.schemas.training import (
    CourseCreate,
    CourseDeletionActionResponse,
    CourseResponse,
    CourseUpdate,
    DeletionRequestResponse,
    LearningMaterialCreate,
    LearningMaterialResponse,
    SendMaterialToBatchesRequest,
    SendMaterialToBatchesResponse,
)

from services.identity.app.core.roles import Permission, Role
from services.identity.app.dependencies.auth import (
    get_current_user,
    require_permissions,
)
from services.training.app.routers.assessments import get_learner_allowed_dept_ids
from services.training.app.services.course_sync import (
    ensure_department_courses_synced,
    initiate_or_approve_deletion,
)
from services.training.app.services.teacher_scope import (
    IdentitySessionLocal,
    get_common_department_ids,
    get_teacher_assigned_dept_ids,
    is_common_department_id,
    require_teacher_department_access,
    role_str,
)

router = APIRouter(prefix="/courses", tags=["Courses"])

MATERIALS_UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "materials")
)
os.makedirs(MATERIALS_UPLOAD_DIR, exist_ok=True)

ALLOWED_MATERIAL_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".txt",
    ".md",
    ".csv",
    ".xlsx",
    ".xls",
    ".zip",
}
MAX_MATERIAL_BYTES = 25 * 1024 * 1024  # 25 MB upload limit


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_department(db: Session, department_id: int):
    department = db.get(Department, department_id)

    if not department:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )

    return department


def get_learner_approved_dept_ids(db: Session, user_id: int) -> set[int] | None:
    """
    Returns allowed department IDs for a learner:
    - None until all assigned onboarding assessments are completed.
    - {All / Common} after assessments complete until department is approved.
    - {approved department, All / Common} once approved.
    """
    return get_learner_allowed_dept_ids(db, user_id)


def _ensure_learner_course_access(db: Session, current_user, course: Course) -> None:
    if current_user.role != Role.LEARNER:
        require_teacher_department_access(db, current_user, course.department_id)
        return
    if not course.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This course is not published",
        )
    allowed_dept_ids = get_learner_approved_dept_ids(db, current_user.id)
    if not allowed_dept_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your department allocation is pending instructor/admin approval. Courses and study materials will unlock once approved.",
        )
    if course.department_id not in allowed_dept_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to study materials outside your approved department.",
        )


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permissions(Permission.MANAGE_COURSES)
    ),
):
    require_teacher_department_access(db, current_user, payload.department_id)
    dept = require_department(db, payload.department_id)

    existing_for_dept = db.scalars(
        select(Course).where(Course.department_id == payload.department_id)
    ).first()
    if existing_for_dept is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Department '{dept.name}' already has Course '{existing_for_dept.title}'. "
                "Courses are maintained 1:1 with departments."
            ),
        )

    course = Course(**payload.model_dump())
    db.add(course)

    try:
        db.commit()
        db.refresh(course)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create course because of a data conflict",
        )

    return CourseResponse(
        id=course.id,
        department_id=course.department_id,
        department_name=dept.name,
        title=course.title,
        description=course.description,
        is_published=course.is_published,
    )


@router.get("", response_model=list[CourseResponse])
def list_courses(
    department_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ensure_department_courses_synced(db, seed_common_if_empty=False)
    query = select(Course).order_by(Course.id)

    if current_user.role == Role.LEARNER:
        allowed_dept_ids = get_learner_approved_dept_ids(db, current_user.id)
        if not allowed_dept_ids:
            # Student has not been approved for a department yet: unlock nothing
            return []
        query = query.where(
            Course.is_published == True,
            Course.department_id.in_(allowed_dept_ids),
        )
    elif role_str(current_user) == Role.TEACHER.value:
        allowed_teacher_depts = get_teacher_assigned_dept_ids(db, int(current_user.id))
        if not allowed_teacher_depts:
            return []
        common_dept_ids = get_common_department_ids(db)
        visible_dept_ids = allowed_teacher_depts | common_dept_ids
        if department_id is not None:
            if int(department_id) not in visible_dept_ids:
                return []
            query = query.where(Course.department_id == department_id)
        else:
            query = query.where(Course.department_id.in_(visible_dept_ids))
    elif department_id is not None:
        query = query.where(Course.department_id == department_id)

    courses = db.scalars(query).all()
    if not courses:
        return []

    dept_ids = {c.department_id for c in courses}
    depts = db.scalars(select(Department).where(Department.id.in_(dept_ids))).all()
    dept_map = {d.id: d.name for d in depts}

    return [
        CourseResponse(
            id=c.id,
            department_id=c.department_id,
            department_name=dept_map.get(c.department_id),
            title=c.title,
            description=c.description,
            is_published=c.is_published,
        )
        for c in courses
    ]


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    _ensure_learner_course_access(db, current_user, course)
    require_teacher_department_access(
        db, current_user, course.department_id, allow_common_read=True
    )

    dept = db.get(Department, course.department_id)
    return CourseResponse(
        id=course.id,
        department_id=course.department_id,
        department_name=dept.name if dept else None,
        title=course.title,
        description=course.description,
        is_published=course.is_published,
    )


@router.patch(
    "/{course_id}",
    response_model=CourseResponse,
)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permissions(Permission.MANAGE_COURSES)
    ),
):
    course = db.get(Course, course_id)

    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    require_teacher_department_access(db, current_user, course.department_id)
    changes = payload.model_dump(exclude_unset=True)

    if changes.get("department_id") is not None:
        require_teacher_department_access(db, current_user, changes["department_id"])
        require_department(db, changes["department_id"])

    for field, value in changes.items():
        setattr(course, field, value)

    try:
        db.commit()
        db.refresh(course)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update course because of a data conflict",
        )

    return course


@router.delete(
    "/{course_id}",
    response_model=CourseDeletionActionResponse,
)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_str(current_user) != Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin can delete a course or department.",
        )

    from fastapi.encoders import jsonable_encoder
    from fastapi.responses import JSONResponse

    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    dept = db.get(Department, course.department_id)
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paired department not found",
        )

    deleted, req_data = initiate_or_approve_deletion(
        db,
        department=dept,
        target_type="course",
        course_id=course.id,
        current_user_id=int(current_user.id),
        identity_session_factory=IdentitySessionLocal,
    )
    body = CourseDeletionActionResponse(
        status="deleted" if deleted else "pending_approval",
        department_id=req_data["department_id"],
        course_id=req_data["course_id"],
        message=(
            f"Deleted course '{course.title}' and its paired Department '{req_data['department_name']}'."
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


# --------------------------------------------------
# Learning Materials (PDF Uploads & Resource Links)
# --------------------------------------------------

@router.get(
    "/{course_id}/materials",
    response_model=list[LearningMaterialResponse],
)
def list_course_materials(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    role = role_str(current_user)
    if role == Role.LEARNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Teachers and SuperAdmin can access the Course Permanent Resource Vault.",
        )
    if role == Role.TEACHER.value:
        require_teacher_department_access(
            db, current_user, course.department_id, allow_common_read=True
        )

    return db.scalars(
        select(LearningMaterial)
        .where(
            LearningMaterial.course_id == course_id,
            LearningMaterial.is_active == True,
        )
        .order_by(LearningMaterial.id.desc())
    ).all()


@router.get(
    "/{course_id}/delivered-materials",
    response_model=list[LearningMaterialResponse],
)
def list_delivered_course_materials(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    role = role_str(current_user)
    if role == Role.LEARNER.value:
        approved_depts = get_learner_approved_dept_ids(db, int(current_user.id)) or set()
        if not approved_depts:
            return []
        if not is_common_department_id(db, course.department_id):
            _ensure_learner_course_access(db, current_user, course)
        active_cohort_ids = list(
            db.scalars(
                select(Cohort.id)
                .join(CohortMember, CohortMember.cohort_id == Cohort.id)
                .where(
                    Cohort.department_id.in_(approved_depts),
                    Cohort.status != "completed",
                    CohortMember.user_id == int(current_user.id),
                    CohortMember.status == "active",
                )
            ).all()
        )
        if not active_cohort_ids:
            return []
        return db.scalars(
            select(LearningMaterial)
            .join(
                CohortMaterialDelivery,
                CohortMaterialDelivery.material_id == LearningMaterial.id,
            )
            .where(
                CohortMaterialDelivery.course_id == course_id,
                CohortMaterialDelivery.cohort_id.in_(active_cohort_ids),
                LearningMaterial.is_active == True,  # noqa: E712
            )
            .distinct()
            .order_by(LearningMaterial.id.desc())
        ).all()

    if role == Role.TEACHER.value:
        require_teacher_department_access(
            db, current_user, course.department_id, allow_common_read=True
        )

    return db.scalars(
        select(LearningMaterial)
        .join(
            CohortMaterialDelivery,
            CohortMaterialDelivery.material_id == LearningMaterial.id,
        )
        .where(
            CohortMaterialDelivery.course_id == course_id,
            LearningMaterial.is_active == True,  # noqa: E712
        )
        .distinct()
        .order_by(LearningMaterial.id.desc())
    ).all()


@router.post(
    "/{course_id}/materials",
    response_model=LearningMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_material_link(
    course_id: int,
    payload: LearningMaterialCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permissions(Permission.MANAGE_MATERIALS)
    ),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    require_teacher_department_access(db, current_user, course.department_id, allow_common_read=True)
    material = LearningMaterial(
        course_id=course_id,
        title=payload.title.strip(),
        material_type=payload.material_type,
        storage_key=payload.storage_key.strip(),
        is_active=True,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.post(
    "/{course_id}/materials/upload",
    response_model=LearningMaterialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_material_file(
    course_id: int,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(
        require_permissions(Permission.MANAGE_MATERIALS)
    ),
):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )

    require_teacher_department_access(db, current_user, course.department_id, allow_common_read=True)
    # Strip any client directory prefix and enforce extension/size rules
    raw_name = os.path.basename(file.filename or "document.pdf")
    stem, ext = os.path.splitext(raw_name)
    ext = ext.lower()
    if ext not in ALLOWED_MATERIAL_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file extension '{ext or 'none'}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_MATERIAL_EXTENSIONS))}"
            ),
        )

    clean_stem = "".join(c for c in stem if c.isalnum() or c in "._- ").strip(" .")
    if not clean_stem:
        clean_stem = "document"
    safe_filename = f"{clean_stem[:120]}{ext}"
    unique_name = f"{uuid.uuid4().hex[:12]}_{safe_filename}"
    file_path = os.path.abspath(os.path.join(MATERIALS_UPLOAD_DIR, unique_name))
    try:
        valid_target = os.path.commonpath([MATERIALS_UPLOAD_DIR, file_path]) == MATERIALS_UPLOAD_DIR
    except ValueError:
        valid_target = False
    if not valid_target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload path",
        )

    total_bytes = 0
    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = file.file.read(65536)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_MATERIAL_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Uploaded file exceeds 25 MB size limit",
                    )
                buffer.write(chunk)
        if total_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty",
            )
    except HTTPException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except OSError:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file",
        )

    material = LearningMaterial(
        course_id=course_id,
        title=title.strip() if title.strip() else safe_filename,
        material_type="pdf" if safe_filename.lower().endswith(".pdf") else "doc",
        storage_key=file_path,
        is_active=True,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.get(
    "/{course_id}/materials/{material_id}/file",
)
def download_material_file(
    course_id: int,
    material_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    material = db.get(LearningMaterial, material_id)
    if not material or material.course_id != course_id or not material.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning material not found",
        )

    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    role = role_str(current_user)
    if role == Role.LEARNER.value:
        approved_depts = get_learner_approved_dept_ids(db, int(current_user.id)) or set()
        if not approved_depts:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Department approval required to download learning files.",
            )
        has_delivery = db.scalars(
            select(CohortMaterialDelivery.id)
            .join(Cohort, Cohort.id == CohortMaterialDelivery.cohort_id)
            .join(CohortMember, CohortMember.cohort_id == Cohort.id)
            .where(
                CohortMaterialDelivery.material_id == material_id,
                Cohort.status != "completed",
                Cohort.department_id.in_(approved_depts),
                CohortMember.user_id == int(current_user.id),
                CohortMember.status == "active",
            )
        ).first()
        if not has_delivery:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This resource has not been sent to any active batch you belong to.",
            )
    elif role == Role.TEACHER.value:
        require_teacher_department_access(
            db, current_user, course.department_id, allow_common_read=True
        )

    abs_path = os.path.abspath(material.storage_key)
    try:
        is_inside_upload_dir = (
            os.path.commonpath([MATERIALS_UPLOAD_DIR, abs_path]) == MATERIALS_UPLOAD_DIR
        )
    except ValueError:
        is_inside_upload_dir = False

    if not is_inside_upload_dir or not os.path.isfile(abs_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage server",
        )

    filename = os.path.basename(abs_path)
    # Strip uuid prefix for user display
    display_name = filename.split("_", 1)[-1] if "_" in filename else filename
    media_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"

    return FileResponse(
        abs_path,
        media_type=media_type,
        filename=display_name,
    )


@router.delete(
    "/{course_id}/materials/{material_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_material(
    course_id: int,
    material_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if role_str(current_user) != Role.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SuperAdmin can permanently delete resources from the Course Resource Vault.",
        )

    material = db.get(LearningMaterial, material_id)
    if not material or material.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning material not found",
        )

    from sqlalchemy import delete as sa_delete

    db.execute(
        sa_delete(CohortMaterialDelivery).where(CohortMaterialDelivery.material_id == material_id)
    )
    material.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{course_id}/materials/{material_id}/send-to-batches",
    response_model=SendMaterialToBatchesResponse,
)
def send_material_to_batches(
    course_id: int,
    material_id: int,
    payload: SendMaterialToBatchesRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = role_str(current_user)
    if role not in {Role.SUPERADMIN.value, Role.TEACHER.value}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only assigned Teachers or SuperAdmin can send Vault resources to active batches.",
        )

    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    material = db.scalar(
        select(LearningMaterial).where(
            LearningMaterial.id == material_id,
            LearningMaterial.course_id == course_id,
            LearningMaterial.is_active == True,  # noqa: E712
        )
    )
    if not material:
        raise HTTPException(status_code=404, detail="Resource not found in this Course Vault")

    allowed_teacher_depts: set[int] | None = None
    if role == Role.TEACHER.value:
        allowed_teacher_depts = require_teacher_department_access(
            db, current_user, course.department_id, allow_common_read=True
        )

    unique_cohort_ids = list(dict.fromkeys(int(cid) for cid in payload.cohort_ids if int(cid) > 0))
    if not unique_cohort_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Select at least one active batch to send this resource.",
        )

    cohorts = db.scalars(select(Cohort).where(Cohort.id.in_(unique_cohort_ids))).all()
    cohort_by_id = {int(c.id): c for c in cohorts}
    if len(cohort_by_id) != len(unique_cohort_ids):
        raise HTTPException(status_code=404, detail="One or more selected batches were not found")

    is_common_course = is_common_department_id(db, course.department_id)
    teacher_cohort_links = (
        {
            int(ct.cohort_id)
            for ct in db.scalars(
                select(CohortTeacher).where(CohortTeacher.user_id == int(current_user.id))
            ).all()
        }
        if role == Role.TEACHER.value
        else set()
    )
    cohorts_with_teachers = (
        {
            int(cid)
            for cid in db.scalars(
                select(CohortTeacher.cohort_id).where(CohortTeacher.cohort_id.in_(unique_cohort_ids))
            ).all()
        }
        if role == Role.TEACHER.value
        else set()
    )

    delivered_names: list[str] = []
    for cid in unique_cohort_ids:
        cohort = cohort_by_id[cid]
        if (cohort.status or "").lower() == "completed":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Batch '{cohort.name}' has already ended and cannot receive resources.",
            )
        if not is_common_course and int(cohort.department_id) != int(course.department_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Batch '{cohort.name}' belongs to a different department. "
                    "You can only send this course resource to batches of the same department."
                ),
            )
        if role == Role.TEACHER.value:
            assert allowed_teacher_depts is not None
            if int(cohort.department_id) not in allowed_teacher_depts:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"You are not assigned to Batch '{cohort.name}'s department.",
                )
            if cid in cohorts_with_teachers and cid not in teacher_cohort_links:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Batch '{cohort.name}' is assigned to different teacher(s).",
                )

        existing = db.scalar(
            select(CohortMaterialDelivery).where(
                CohortMaterialDelivery.cohort_id == cid,
                CohortMaterialDelivery.material_id == material.id,
            )
        )
        if existing is None:
            db.add(
                CohortMaterialDelivery(
                    cohort_id=cid,
                    course_id=course.id,
                    material_id=material.id,
                    sent_by_user_id=int(current_user.id),
                )
            )
        delivered_names.append(cohort.name)

    db.commit()
    total_deliveries = len(
        db.scalars(
            select(CohortMaterialDelivery.id).where(
                CohortMaterialDelivery.material_id == material.id
            )
        ).all()
    )
    return SendMaterialToBatchesResponse(
        material_id=material.id,
        course_id=course.id,
        delivered_cohort_ids=unique_cohort_ids,
        delivered_batch_names=delivered_names,
        total_deliveries=total_deliveries,
    )
