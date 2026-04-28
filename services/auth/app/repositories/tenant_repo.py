import uuid
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.tenant import Tenant


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, slug: str, name: str, plan: str = "starter") -> Tenant:
        tenant = Tenant(slug=slug, name=name, plan=plan)
        self._session.add(tenant)
        await self._session.flush()
        return tenant

    async def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        return await self._session.get(Tenant, tenant_id)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self._session.execute(
            select(Tenant).where(Tenant.slug == slug, Tenant.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def count_active_users(self, tenant_id: uuid.UUID) -> int:
        from sqlalchemy import func

        from ..models.user import User

        result = await self._session.execute(
            select(func.count()).where(
                User.tenant_id == tenant_id, User.is_active, User.deleted_at.is_(None)
            )
        )
        return result.scalar_one()

    async def update(self, tenant: Tenant, **kwargs: object) -> Tenant:
        for k, v in kwargs.items():
            setattr(tenant, k, v)
        await self._session.flush()
        return tenant

    async def soft_delete(self, tenant: Tenant) -> None:
        from datetime import datetime

        tenant.deleted_at = datetime.now(UTC)
        tenant.is_active = False
        await self._session.flush()
