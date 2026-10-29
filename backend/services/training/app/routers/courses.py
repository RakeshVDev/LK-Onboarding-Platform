
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.training.app.db.session import SessionLocal
from services.training.app.models.entities import Course, Department
from services.training.app.schemas.training import (
    CourseCreate,
    CourseResponse,
    CourseUpdate,
)

from services.identity.app.core.roles import Permission
from services.identity.app.dependencies.auth import (
    get_current_user,
    require_permissions,
)

router = APIRouter(prefix="/courses", tags=["Courses"])


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
    require_department(db, payload.department_id)

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

    return course


@router.get("", response_model=list[CourseResponse])
def list_courses(
    department_id: int | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Course).order_by(Course.id)

    if department_id is not None:
        query = query.where(
            Course.department_id == department_id
        )

    # TODO: Filter results by teacher assignments and learner enrollments.
    # Authentication alone does not grant access to every course.
    return db.scalars(query).all()


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

    # TODO: Enforce teacher-assignment and learner-enrollment checks
    # before returning course details.
    return course


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
