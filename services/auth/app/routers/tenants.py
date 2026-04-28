from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_user, require_tenant_admin
from ..models.user import User
from ..schemas.tenant import TenantCreate, TenantResponse, TenantStats, TenantUpdate
from ..services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse, status_code=201)
async def register_tenant(
    body: TenantCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> object:
    svc = TenantService(session)
    tenant, _ = await svc.create_tenant(
        slug=body.slug,
        name=body.name,
        plan=body.plan,
        admin_email=body.admin_email,
        admin_password=body.admin_password,
        admin_full_name=body.admin_full_name,
    )
    return tenant


@router.get("/me", response_model=TenantResponse)
async def get_my_tenant(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> object:
    svc = TenantService(session)
    return await svc.get_tenant(current_user.tenant_id)


@router.patch("/me", response_model=TenantResponse)
async def update_my_tenant(
    body: TenantUpdate,
    current_user: Annotated[User, Depends(require_tenant_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> object:
    from ..repositories.tenant_repo import TenantRepository

    repo = TenantRepository(session)
    tenant = await repo.get_by_id(current_user.tenant_id)
    if not tenant:
        from shared.core.exceptions import NotFoundError

        raise NotFoundError("Tenant not found")
    updates = body.model_dump(exclude_none=True)
    return await repo.update(tenant, **updates)


@router.get("/me/stats", response_model=TenantStats)
async def get_tenant_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> object:
    svc = TenantService(session)
    return await svc.get_stats(current_user.tenant_id)


@router.delete("/me", status_code=204)
async def delete_tenant(
    current_user: Annotated[User, Depends(require_tenant_admin)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    from ..repositories.tenant_repo import TenantRepository

    repo = TenantRepository(session)
    tenant = await repo.get_by_id(current_user.tenant_id)
    if tenant:
        await repo.soft_delete(tenant)
        await session.commit()
