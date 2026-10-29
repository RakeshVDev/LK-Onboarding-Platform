
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ManagedRole = Literal["admin", "teacher", "learner"]


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=10, max_length=128)
    role: ManagedRole = "learner"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()

        if (
            "@" not in value
            or value.startswith("@")
            or value.endswith("@")
            or " " in value
        ):
            raise ValueError("Enter a valid email address")

        return value


class UserStatusUpdateRequest(BaseModel):
    is_active: bool
