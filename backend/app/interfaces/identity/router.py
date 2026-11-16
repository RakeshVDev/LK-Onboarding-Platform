"""Identity interface router & schemas re-exports."""

from services.identity.app.routers.onboarding import router
from services.identity.app.schemas.onboarding import (
    AdminDepartmentApproveRequest,
    DepartmentSelectRequest,
    NavItemPermission,
    NavigationPermissionsResponse,
)

__all__ = [
    "AdminDepartmentApproveRequest",
    "DepartmentSelectRequest",
    "NavItemPermission",
    "NavigationPermissionsResponse",
    "router",
]

