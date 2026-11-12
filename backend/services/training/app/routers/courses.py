
import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, Response, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.training.app.db.session import SessionLocal
from services.training.app.models.entities import Course, Department, LearningMaterial, StudentDepartmentRequest
from services.training.app.schemas.training import (
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    LearningMaterialCreate,
    LearningMaterialResponse,
)

from services.identity.app.core.roles import Permission, Role
from services.identity.app.dependencies.auth import (
    get_current_user,
    require_permissions,
)

router = APIRouter(prefix="/courses", tags=["Courses"])

MATERIALS_UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "materials")
)
os.makedirs(MATERIALS_UPLOAD_DIR, exist_ok=True)


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
    Returns set of allowed department IDs (the student's approved department + All/Common department).
    If the learner has no approved department allocation, returns None.
    """
    approved_req = db.scalar(
        select(StudentDepartmentRequest).where(
            StudentDepartmentRequest.user_id == user_id,
            StudentDepartmentRequest.status == "approved",
        )
    )
    if not approved_req:
        return None

    allowed_ids = {approved_req.department_id}
    common_dept = db.scalar(
        select(Department).where(
            Department.name.in_(["All / Common", "All/Common", "Common"])
        )
    )
    if common_dept:
        allowed_ids.add(common_dept.id)

    return allowed_ids


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
    dept = require_department(db, payload.department_id)

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
    query = select(Course).order_by(Course.id)

    if current_user.role == Role.LEARNER:
        allowed_dept_ids = get_learner_approved_dept_ids(db, current_user.id)
        if not allowed_dept_ids:
            # Student has not been approved for a department yet: unlock nothing
            return []
        query = query.where(Course.department_id.in_(allowed_dept_ids))
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

    if current_user.role == Role.LEARNER:
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

    changes = payload.model_dump(exclude_unset=True)

    if changes.get("department_id") is not None:
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
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_course(
    course_id: int,
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

    db.delete(course)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot delete this course while "
                "dependent records exist"
            ),
        )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
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

    if current_user.role == Role.LEARNER:
        allowed_dept_ids = get_learner_approved_dept_ids(db, current_user.id)
        if not allowed_dept_ids or course.department_id not in allowed_dept_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to study materials outside your approved department.",
            )

    return db.scalars(
        select(LearningMaterial)
        .where(
            LearningMaterial.course_id == course_id,
            LearningMaterial.is_active == True,
        )
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

    # Sanitize and store filename
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in "._- ")
    if not safe_filename:
        safe_filename = "document.pdf"
    unique_name = f"{uuid.uuid4().hex[:12]}_{safe_filename}"
    file_path = os.path.join(MATERIALS_UPLOAD_DIR, unique_name)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}",
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

    if current_user.role == Role.LEARNER:
        allowed_dept_ids = get_learner_approved_dept_ids(db, current_user.id)
        if not allowed_dept_ids or course.department_id not in allowed_dept_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to study materials outside your approved department.",
            )

    if not os.path.exists(material.storage_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on storage server",
        )

    filename = os.path.basename(material.storage_key)
    # Strip uuid prefix for user display
    display_name = filename.split("_", 1)[-1] if "_" in filename else filename
    media_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"

    return FileResponse(
        material.storage_key,
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
    current_user=Depends(
        require_permissions(Permission.MANAGE_MATERIALS)
    ),
):
    material = db.get(LearningMaterial, material_id)
    if not material or material.course_id != course_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning material not found",
        )

    material.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
