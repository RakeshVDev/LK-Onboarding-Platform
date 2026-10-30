
from pydantic import BaseModel, ConfigDict, Field


class EnrollmentCreate(BaseModel):
    user_id: int = Field(gt=0)


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    user_id: int
    status: str


class EnrollmentStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(enrolled|completed|withdrawn)$")


class SyllabusCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    sequence_order: int = Field(default=1, ge=1)


class SyllabusUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    sequence_order: int | None = Field(default=None, ge=1)


class SyllabusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    description: str | None
    sequence_order: int
