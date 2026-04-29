import uuid
from typing import Annotated, cast

from fastapi import Depends, Request
from shared.core.exceptions import AuthenticationError, AuthorizationError
from shared.core.security.jwt import JWTHandler
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session
from .models.user import User
from .repositories.user_repo import UserRepository


def get_jwt_handler() -> JWTHandler:
    from .main import jwt_handler

    return cast(JWTHandler, jwt_handler)


async def get_current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    user_id_str = getattr(request.state, "user_id", None)
    if not user_id_str:
        raise AuthenticationError("Not authenticated")
    repo = UserRepository(session)
    user = await repo.get_by_id(uuid.UUID(user_id_str))
    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user


async def require_tenant_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    role_names = [ur.role.name for ur in current_user.user_roles]
    if "tenant_admin" not in role_names:
        raise AuthorizationError("Tenant admin role required")
    return current_user


async def require_manager_or_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    role_names = {ur.role.name for ur in current_user.user_roles}
    if not role_names.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Project manager or admin role required")
    return current_user
