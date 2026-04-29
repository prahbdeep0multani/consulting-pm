import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from shared.core.exceptions import AuthorizationError, NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_user, require_tenant_admin
from ..models.user import User
from ..repositories.user_repo import RoleRepository
from ..schemas.role import RoleCreate, RoleResponse, RoleUpdate

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Any]:
    repo = RoleRepository(session)
    return await repo.list_by_tenant(current_user.tenant_id)  # type: ignore[no-any-return]


@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    body: RoleCreate,
    current_user: Annotated[User, Depends(require_tenant_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> object:
    repo = RoleRepository(session)
    role = await repo.create(current_user.tenant_id, body.name, body.permissions)
    await session.commit()
    return role


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> object:
    repo = RoleRepository(session)
    role = await repo.get_by_id(role_id)
    if not role or role.tenant_id != current_user.tenant_id:
        raise NotFoundError("Role not found")
    return role


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    current_user: Annotated[User, Depends(require_tenant_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> object:
    repo = RoleRepository(session)
    role = await repo.get_by_id(role_id)
    if not role or role.tenant_id != current_user.tenant_id:
        raise NotFoundError("Role not found")
    if role.is_system:
        raise AuthorizationError("System roles cannot be modified")
    if body.permissions is not None:
        role = await repo.update(role, body.permissions)
    await session.commit()
    return role


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_tenant_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    repo = RoleRepository(session)
    role = await repo.get_by_id(role_id)
    if not role or role.tenant_id != current_user.tenant_id:
        raise NotFoundError("Role not found")
    if role.is_system:
        raise AuthorizationError("System roles cannot be deleted")
    await repo.delete(role)
    await session.commit()
