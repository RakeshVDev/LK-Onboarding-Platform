
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.training.app.db.session import SessionLocal
from services.training.app.models.entities import Course, CourseEnrollment
from services.training.app.schemas.learning import (
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentStatusUpdate,
)
from services.identity.app.dependencies.auth import get_current_user
from services.training.app.routers.assessments import get_learner_allowed_dept_ids

router = APIRouter(prefix="/courses", tags=["Course Enrolments"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def role_of(user) -> str:
    return str(user.role.value if hasattr(user.role, "value") else user.role)


def is_manager(user) -> bool:
    return role_of(user) in {"superadmin", "admin"}


@router.post(
    "/{course_id}/enrolments",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_enrollment(
    course_id: int,
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = role_of(current_user)

    if role not in {"superadmin", "admin", "learner"}:
        raise HTTPException(status_code=403, detail="Not allowed to enrol users")

    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if role == "learner":
        if payload.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="You can only enrol yourself",
            )
        allowed_dept_ids = get_learner_allowed_dept_ids(db, current_user.id)
        if not allowed_dept_ids or course.department_id not in allowed_dept_ids:
            raise HTTPException(
                status_code=403,
                detail="Courses unlock only after your department selection is approved.",
            )
        if not course.is_published:
            raise HTTPException(
                status_code=400,
                detail="This course is not published",
            )

    enrollment = CourseEnrollment(
        course_id=course_id,
        user_id=payload.user_id,
        status="enrolled",
    )
    db.add(enrollment)

    try:
        db.commit()
        db.refresh(enrollment)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This user is already enrolled in the course",
        )

    return enrollment


@router.get(
    "/{course_id}/enrolments",
    response_model=list[EnrollmentResponse],
)
def list_enrollments(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role = role_of(current_user)

    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    query = select(CourseEnrollment).where(
        CourseEnrollment.course_id == course_id
    )

    if role == "learner":
        allowed_dept_ids = get_learner_allowed_dept_ids(db, current_user.id)
        if not allowed_dept_ids or course.department_id not in allowed_dept_ids:
            raise HTTPException(
                status_code=403,
                detail="Courses unlock only after your department selection is approved.",
            )
        query = query.where(CourseEnrollment.user_id == current_user.id)
    elif role not in {"superadmin", "admin", "teacher"}:
        raise HTTPException(status_code=403, detail="Not allowed")
    elif role == "teacher":
        from services.training.app.services.teacher_scope import require_teacher_department_access
        require_teacher_department_access(db, current_user, course.department_id)

    return db.scalars(query.order_by(CourseEnrollment.id)).all()


@router.patch(
    "/{course_id}/enrolments/{enrollment_id}",
    response_model=EnrollmentResponse,
)
def update_enrollment(
    course_id: int,
    enrollment_id: int,
    payload: EnrollmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not is_manager(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only administrators can update enrolments",
        )

    enrollment = db.get(CourseEnrollment, enrollment_id)

    if not enrollment or enrollment.course_id != course_id:
        raise HTTPException(status_code=404, detail="Enrolment not found")

    enrollment.status = payload.status
    db.commit()
    db.refresh(enrollment)

    return enrollment
