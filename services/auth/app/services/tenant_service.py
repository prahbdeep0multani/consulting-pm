import uuid

from shared.core.exceptions import ConflictError, NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.tenant import Tenant
from ..repositories.tenant_repo import TenantRepository
from ..repositories.user_repo import RoleRepository, UserRepository
from ..security.password import hash_password

_SYSTEM_ROLES = {
    "tenant_admin": ["*:*"],
    "project_manager": [
        "project:read",
        "project:write",
        "task:read",
        "task:write",
        "timelog:read",
        "timelog:approve",
        "resource:read",
        "resource:write",
        "billing:read",
        "client:read",
        "client:write",
    ],
    "consultant": [
        "project:read",
        "task:read",
        "task:write",
        "timelog:read",
        "timelog:write",
        "resource:read",
    ],
    "client_viewer": [
        "project:read",
        "milestone:read",
        "task:read",
    ],
}


class TenantService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tenant_repo = TenantRepository(session)
        self._user_repo = UserRepository(session)
        self._role_repo = RoleRepository(session)

    async def create_tenant(
        self,
        slug: str,
        name: str,
        plan: str,
        admin_email: str,
        admin_password: str,
        admin_full_name: str,
    ) -> tuple[Tenant, object]:
        existing = await self._tenant_repo.get_by_slug(slug)
        if existing:
            raise ConflictError(f"Tenant slug '{slug}' is already taken")

        async with self._session.begin_nested():
            tenant = await self._tenant_repo.create(slug=slug, name=name, plan=plan)

            # Seed system roles
            roles = {}
            for role_name, perms in _SYSTEM_ROLES.items():
                role = await self._role_repo.create(tenant.id, role_name, perms, is_system=True)
                roles[role_name] = role

            # Create admin user
            pw_hash = hash_password(admin_password)
            admin = await self._user_repo.create(tenant.id, admin_email, pw_hash, admin_full_name)
            admin.is_verified = True
            await self._user_repo.assign_role(admin, roles["tenant_admin"])

        await self._session.commit()
        return tenant, admin

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if not tenant or tenant.deleted_at:
            raise NotFoundError("Tenant not found")
        return tenant

    async def get_stats(self, tenant_id: uuid.UUID) -> dict:
        total = await self._tenant_repo.count_active_users(tenant_id)
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        return {
            "user_count": total,
            "active_user_count": total,
            "max_users": tenant.max_users if tenant else 0,
        }
