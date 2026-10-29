
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CohortCreate(BaseModel):
    department_id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=150)
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str = Field(default="planned", max_length=30)


class CohortUpdate(BaseModel):
    department_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=2, max_length=150)
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: str | None = Field(default=None, max_length=30)


class CohortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    name: str
    start_date: datetime | None
    end_date: datetime | None
    status: str
