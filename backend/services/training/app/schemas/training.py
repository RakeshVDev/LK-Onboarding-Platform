
from pydantic import BaseModel, ConfigDict, Field


# ---------- Department schemas ----------

class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    is_active: bool | None = None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    is_active: bool


# ---------- Course schemas ----------

class CourseCreate(BaseModel):
    department_id: int = Field(gt=0)
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    is_published: bool = False


class CourseUpdate(BaseModel):
    department_id: int | None = Field(default=None, gt=0)
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    is_published: bool | None = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    title: str
    description: str | None
    is_published: bool


# ---------- Learning Material schemas ----------

class LearningMaterialCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    material_type: str = Field(default="link", pattern="^(pdf|link|doc|video)$")
    storage_key: str = Field(min_length=1, max_length=1000)


class LearningMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    material_type: str
    storage_key: str
    is_active: bool
