
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from services.identity.app.core.config import settings
from services.identity.app.db.session import SessionLocal
from services.identity.app.models.user import User

from services.identity.app.core.roles import (
    Permission,
    Role,
    ROLE_PERMISSIONS,
)


bearer_scheme = HTTPBearer(auto_error=False)




def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer="lk-identity",
            audience="lk-platform",
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise unauthorized

    user = db.get(User, user_id)

    if user is None or not user.is_active:
        raise unauthorized

    return user


def require_roles(*allowed_roles: str) -> Callable:
    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker


    
def require_roles(*allowed_roles: Role):
    def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        try:
            user_role = Role(current_user.role)
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail="User has no recognized role",
            )

        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient role permissions",
            )

        return current_user

    return role_checker


def require_permissions(*required_permissions: Permission):
    def permission_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        try:
            user_role = Role(current_user.role)
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail="User has no recognized role",
            )

        granted_permissions = ROLE_PERMISSIONS[user_role]

        if not all(
            permission in granted_permissions
            for permission in required_permissions
        ):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions",
            )

        return current_user

    return permission_checker

