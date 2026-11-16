"""Infrastructure persistence models for Identity module."""

from services.identity.app.db.base import Base as IdentityBase
from services.identity.app.models.user import User

__all__ = ["IdentityBase", "User"]

