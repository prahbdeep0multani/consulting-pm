import uuid

from shared.core.exceptions import ConflictError, NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.user_repo import RoleRepository, UserRepository
from ..security.password import hash_password


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._role_repo = RoleRepository(session)

    async def create_user(
        self,
        tenant_id: uuid.UUID,
        email: str,
        password: str,
        full_name: str,
        role_names: list[str],
    ) -> object:
        existing = await self._user_repo.get_by_email(tenant_id, email)
        if existing:
            raise ConflictError(f"User with email '{email}' already exists")

        pw_hash = hash_password(password)
        user = await self._user_repo.create(tenant_id, email, pw_hash, full_name)

        for role_name in role_names:
            role = await self._role_repo.get_by_name(tenant_id, role_name)
            if role:
                await self._user_repo.assign_role(user, role)

        await self._session.commit()
        return user

    async def get_user(self, user_id: uuid.UUID) -> object:
        user = await self._user_repo.get_by_id(user_id)
        if not user or user.deleted_at:
            raise NotFoundError("User not found")
        return user

    async def list_users(self, tenant_id: uuid.UUID, limit: int = 20, offset: int = 0) -> list:
        return await self._user_repo.list_by_tenant(tenant_id, limit, offset)

    async def update_user(self, user_id: uuid.UUID, **kwargs: object) -> object:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return await self._user_repo.update(user, **kwargs)

    async def deactivate_user(self, user_id: uuid.UUID) -> None:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        await self._user_repo.soft_delete(user)
        await self._session.commit()

    async def assign_role(
        self, user_id: uuid.UUID, role_id: uuid.UUID, assigned_by: uuid.UUID
    ) -> None:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        role = await self._role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError("Role not found")
        await self._user_repo.assign_role(user, role, assigned_by)
        await self._session.commit()

    async def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        await self._user_repo.remove_role(user_id, role_id)
        await self._session.commit()
