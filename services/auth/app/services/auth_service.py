import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from shared.core.security.jwt import JWTHandler

from ..models.token import RefreshToken
from ..models.user import User
from ..repositories.tenant_repo import TenantRepository
from ..repositories.token_repo import PasswordResetTokenRepository, RefreshTokenRepository
from ..repositories.user_repo import UserRepository
from ..security.password import hash_password, verify_password


class AuthService:
    def __init__(self, session: AsyncSession, jwt_handler: JWTHandler) -> None:
        self._session = session
        self._jwt = jwt_handler
        self._user_repo = UserRepository(session)
        self._tenant_repo = TenantRepository(session)
        self._token_repo = RefreshTokenRepository(session)
        self._reset_repo = PasswordResetTokenRepository(session)

    async def login(
        self,
        tenant_slug: str,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        tenant = await self._tenant_repo.get_by_slug(tenant_slug)
        if not tenant or not tenant.is_active:
            raise AuthenticationError("Invalid credentials")

        user = await self._user_repo.get_by_email(tenant.id, email)
        if not user or not user.is_active:
            raise AuthenticationError("Invalid credentials")

        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid credentials")

        await self._user_repo.update_last_login(user)
        return await self._issue_token_pair(user, ip_address, user_agent)

    async def refresh(
        self,
        tenant_slug: str,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[str, str]:
        claims = self._jwt.decode_refresh_token(refresh_token)
        token_hash = self._jwt.hash_token(refresh_token)
        stored = await self._token_repo.get_by_hash(token_hash)

        if not stored:
            # Token not found — possible reuse attack
            raise AuthenticationError("Refresh token not found")

        if stored.revoked_at is not None:
            # Reuse detected — revoke entire family
            await self._token_repo.revoke_family(stored.family)
            await self._session.commit()
            raise AuthenticationError("Refresh token reuse detected — all sessions revoked")

        if stored.expires_at < datetime.now(timezone.utc):
            raise AuthenticationError("Refresh token expired")

        # Rotate: revoke old, issue new
        await self._token_repo.revoke(stored)
        user = await self._user_repo.get_by_id(stored.user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        access, refresh = await self._issue_token_pair(user, ip_address, user_agent, family=stored.family)
        await self._session.commit()
        return access, refresh

    async def logout(self, refresh_token: str) -> None:
        token_hash = self._jwt.hash_token(refresh_token)
        stored = await self._token_repo.get_by_hash(token_hash)
        if stored and not stored.revoked_at:
            await self._token_repo.revoke(stored)
            await self._session.commit()

    async def logout_all(self, user_id: uuid.UUID) -> None:
        await self._token_repo.revoke_all_for_user(user_id)
        await self._session.commit()

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")
        user.password_hash = hash_password(new_password)
        await self._token_repo.revoke_all_for_user(user.id)
        await self._session.commit()

    async def forgot_password(self, tenant_slug: str, email: str) -> str | None:
        """Returns reset token (plaintext) or None if user not found (silent fail)."""
        tenant = await self._tenant_repo.get_by_slug(tenant_slug)
        if not tenant:
            return None
        user = await self._user_repo.get_by_email(tenant.id, email)
        if not user:
            return None

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await self._reset_repo.create(user.id, token_hash, expires_at)
        await self._session.commit()
        return raw_token

    async def reset_password(self, raw_token: str, new_password: str) -> None:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        stored = await self._reset_repo.get_by_hash(token_hash)
        if not stored:
            raise AuthenticationError("Invalid or expired reset token")
        user = await self._user_repo.get_by_id(stored.user_id)
        if not user:
            raise NotFoundError("User not found")
        user.password_hash = hash_password(new_password)
        await self._reset_repo.mark_used(stored)
        await self._token_repo.revoke_all_for_user(user.id)
        await self._session.commit()

    async def _issue_token_pair(
        self,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
        family: uuid.UUID | None = None,
    ) -> tuple[str, str]:
        role_names = [ur.role.name for ur in user.user_roles]
        permissions: list[str] = []
        for ur in user.user_roles:
            permissions.extend(ur.role.permissions)
        permissions = list(set(permissions))

        access = self._jwt.create_access_token(user.id, user.tenant_id, role_names, permissions)
        raw_refresh, refresh_hash = self._jwt.create_refresh_token(user.id, user.tenant_id, family)

        new_family = uuid.UUID(self._jwt.decode_refresh_token(raw_refresh).family or str(uuid.uuid4()))
        expires_at = datetime.now(timezone.utc) + timedelta(days=self._jwt._refresh_expire)
        await self._token_repo.create(
            user_id=user.id,
            tenant_id=user.tenant_id,
            token_hash=refresh_hash,
            family=new_family,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return access, raw_refresh
