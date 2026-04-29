import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_user, require_tenant_admin
from ..models.user import User
from ..schemas.user import UserResponse, UserUpdate
from ..services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _to_response(user: User) -> UserResponse:
    roles = [{"id": ur.role_id, "name": ur.role.name} for ur in user.user_roles]
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        last_login_at=user.last_login_at,
        roles=roles,  # type: ignore[arg-type]
        created_at=user.created_at,
    )


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(require_tenant_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = 20,
    offset: int = 0,
) -> list[UserResponse]:
    svc = UserService(session)
    users = await svc.list_users(current_user.tenant_id, limit, offset)
    return [_to_response(u) for u in users]


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return _to_response(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    svc = UserService(session)
    updated = await svc.update_user(current_user.id, **body.model_dump(exclude_none=True))
    return _to_response(updated)  # type: ignore[arg-type]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    svc = UserService(session)
    user = await svc.get_user(user_id)
    return _to_response(user)  # type: ignore[arg-type]


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: Annotated[User, Depends(require_tenant_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    svc = UserService(session)
    updated = await svc.update_user(user_id, **body.model_dump(exclude_none=True))
    return _to_response(updated)  # type: ignore[arg-type]


@router.delete("/{user_id}", status_code=204)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_tenant_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    svc = UserService(session)
    await svc.deactivate_user(user_id)


@router.post("/{user_id}/roles/{role_id}", status_code=204)
async def assign_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_tenant_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    svc = UserService(session)
    await svc.assign_role(user_id, role_id, current_user.id)


@router.delete("/{user_id}/roles/{role_id}", status_code=204)
async def remove_role(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_tenant_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    svc = UserService(session)
    await svc.remove_role(user_id, role_id)
