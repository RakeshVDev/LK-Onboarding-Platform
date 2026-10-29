
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.training.app.db.session import SessionLocal
from services.training.app.models.entities import Cohort, Department
from services.training.app.schemas.cohort import (
    CohortCreate,
    CohortResponse,
    CohortUpdate,
)

router = APIRouter(prefix="/cohorts", tags=["Cohorts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_department(db: Session, department_id: int):
    if not db.get(Department, department_id):
        raise HTTPException(status_code=404, detail="Department not found")


@router.post("", response_model=CohortResponse, status_code=status.HTTP_201_CREATED)
def create_cohort(payload: CohortCreate, db: Session = Depends(get_db)):
    validate_department(db, payload.department_id)

    if (
        payload.start_date
        and payload.end_date
        and payload.end_date < payload.start_date
    ):
        raise HTTPException(
            status_code=422,
            detail="end_date must be on or after start_date",
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

    cohort = Cohort(**payload.model_dump())
    db.add(cohort)
    db.commit()
    db.refresh(cohort)
    return cohort


@router.get("", response_model=list[CohortResponse])
def list_cohorts(
    department_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = select(Cohort).order_by(Cohort.id)
    if department_id is not None:
        query = query.where(Cohort.department_id == department_id)
    return db.scalars(query).all()


@router.get("/{cohort_id}", response_model=CohortResponse)
def get_cohort(cohort_id: int, db: Session = Depends(get_db)):
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")
    return cohort


@router.patch("/{cohort_id}", response_model=CohortResponse)
def update_cohort(
    cohort_id: int,
    payload: CohortUpdate,
    db: Session = Depends(get_db),
):
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    changes = payload.model_dump(exclude_unset=True)

    if changes.get("department_id") is not None:
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
        setattr(cohort, field, value)

    db.commit()
    db.refresh(cohort)
    return cohort


@router.delete("/{cohort_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cohort(cohort_id: int, db: Session = Depends(get_db)):
    cohort = db.get(Cohort, cohort_id)
    if not cohort:
        raise HTTPException(status_code=404, detail="Cohort not found")

    db.delete(cohort)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cannot delete this cohort while dependent records exist",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)

