
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.training.app.db.session import SessionLocal
from services.training.app.models.entities import Course, SyllabusItem
from services.training.app.schemas.learning import (
    SyllabusCreate,
    SyllabusResponse,
    SyllabusUpdate,
)
from services.identity.app.dependencies.auth import (
    get_current_user,
    require_permissions,
)
from services.identity.app.core.roles import Permission

router = APIRouter(prefix="/courses", tags=["Course Syllabus"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_course(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.get(
    "/{course_id}/syllabus",
    response_model=list[SyllabusResponse],
)
def list_syllabus(
    course_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    course = require_course(db, course_id)

    if not course.is_published and current_user.role not in {
        "superadmin", "admin"
    }:
        raise HTTPException(status_code=403, detail="Course is not published")

    query = (
        select(SyllabusItem)
        .where(SyllabusItem.course_id == course_id)
        .order_by(SyllabusItem.sequence_order, SyllabusItem.id)
    )
    return db.scalars(query).all()


@router.post(
    "/{course_id}/syllabus",
    response_model=SyllabusResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_syllabus_item(
    course_id: int,
    payload: SyllabusCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(Permission.MANAGE_COURSES)),
):
    require_course(db, course_id)

    item = SyllabusItem(course_id=course_id, **payload.model_dump())
    db.add(item)

    try:
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not create syllabus item")

    return item


@router.patch(
    "/{course_id}/syllabus/{item_id}",
    response_model=SyllabusResponse,
)
def update_syllabus_item(
    course_id: int,
    item_id: int,
    payload: SyllabusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(Permission.MANAGE_COURSES)),
):
    item = db.get(SyllabusItem, item_id)

    if not item or item.course_id != course_id:
        raise HTTPException(status_code=404, detail="Syllabus item not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete(
    "/{course_id}/syllabus/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_syllabus_item(
    course_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permissions(Permission.MANAGE_COURSES)),
):
    item = db.get(SyllabusItem, item_id)

    if not item or item.course_id != course_id:
        raise HTTPException(status_code=404, detail="Syllabus item not found")

    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
