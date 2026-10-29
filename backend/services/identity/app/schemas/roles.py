
from pydantic import BaseModel, ConfigDict, Field

from services.identity.app.core.roles import Role


class RoleUpdateRequest(BaseModel):
    role: Role


class RoleUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    is_active: bool
