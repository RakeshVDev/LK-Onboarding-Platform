
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CohortCreate(BaseModel):
    department_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=150)
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str = Field(default="active", max_length=30)
    teacher_ids: list[int] = Field(min_length=1, max_length=5)
    excluded_learner_ids: list[int] = Field(default_factory=list)


class CohortTeachersUpdate(BaseModel):
    teacher_ids: list[int] = Field(min_length=1, max_length=5)


class CohortUpdate(BaseModel):
    department_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=2, max_length=150)
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str | None = Field(default=None, max_length=30)


class CohortTeacherInfo(BaseModel):
    id: int
    full_name: str
    email: str


class CohortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    department_name: str | None = None
    course_id: int | None = None
    name: str
    start_date: datetime | None
    end_date: datetime | None
    status: str
    teacher_ids: list[int] = Field(default_factory=list)
    teachers: list[CohortTeacherInfo] = Field(default_factory=list)
    member_ids: list[int] = Field(default_factory=list)
    learner_count: int = 0
    material_count: int = 0


class CohortCandidateUser(BaseModel):
    id: int
    full_name: str
    email: str
    assigned_department_ids: list[int] = Field(default_factory=list)


class CohortDepartmentCandidatesResponse(BaseModel):
    department_id: int
    learners: list[CohortCandidateUser] = Field(default_factory=list)
    teachers: list[CohortCandidateUser] = Field(default_factory=list)


class CohortDeliveredMaterialResponse(BaseModel):
    id: int
    cohort_id: int
    course_id: int
    material_id: int
    title: str
    material_type: str
    storage_key: str
    source_department_name: str | None = None
    sent_by_user_id: int
    sent_by_name: str | None = None
    sent_at: datetime


class CohortMemberCreate(BaseModel):
    user_id: int = Field(gt=0)
    status: str = Field(default="active", max_length=30)


class CohortMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cohort_id: int
    user_id: int
    joined_at: datetime
    status: str
