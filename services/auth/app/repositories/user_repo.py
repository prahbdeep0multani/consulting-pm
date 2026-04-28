import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.user import Role, User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, tenant_id: uuid.UUID, email: str, password_hash: str, full_name: str
    ) -> User:
        user = User(
            tenant_id=tenant_id, email=email, password_hash=password_hash, full_name=full_name
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, tenant_id: uuid.UUID, email: str) -> User | None:
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(User.tenant_id == tenant_id, User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> list[User]:
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(User.tenant_id == tenant_id, User.deleted_at.is_(None))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update(self, user: User, **kwargs: object) -> User:
        for k, v in kwargs.items():
            setattr(user, k, v)
        user.updated_at = datetime.now(UTC)
        await self._session.flush()
        return user

    async def update_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()

    async def assign_role(
        self, user: User, role: Role, assigned_by: uuid.UUID | None = None
    ) -> None:
        existing = await self._session.execute(
            select(UserRole).where(UserRole.user_id == user.id, UserRole.role_id == role.id)
        )
        if existing.scalar_one_or_none() is None:
            user_role = UserRole(user_id=user.id, role_id=role.id, assigned_by=assigned_by)
            self._session.add(user_role)
            await self._session.flush()

    async def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        result = await self._session.execute(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        user_role = result.scalar_one_or_none()
        if user_role:
            await self._session.delete(user_role)

    async def soft_delete(self, user: User) -> None:
        user.deleted_at = datetime.now(UTC)
        user.is_active = False
        await self._session.flush()


class RoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, tenant_id: uuid.UUID, name: str, permissions: list[str], is_system: bool = False
    ) -> Role:
        role = Role(tenant_id=tenant_id, name=name, permissions=permissions, is_system=is_system)
        self._session.add(role)
        await self._session.flush()
        return role

    async def get_by_id(self, role_id: uuid.UUID) -> Role | None:
        return await self._session.get(Role, role_id)

    async def get_by_name(self, tenant_id: uuid.UUID, name: str) -> Role | None:
        result = await self._session.execute(
            select(Role).where(Role.tenant_id == tenant_id, Role.name == name)
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Role]:
        result = await self._session.execute(select(Role).where(Role.tenant_id == tenant_id))
        return list(result.scalars().all())

    async def update(self, role: Role, permissions: list[str]) -> Role:
        role.permissions = permissions
        await self._session.flush()
        return role

    async def delete(self, role: Role) -> None:
        await self._session.delete(role)
