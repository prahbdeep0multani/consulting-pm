import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from pydantic import BaseModel

from shared.core.exceptions import AuthenticationError

ALGORITHM = "RS256"


class TokenClaims(BaseModel):
    sub: str  # user_id
    tenant_id: str
    roles: list[str]
    permissions: list[str]
    exp: int
    iat: int
    jti: str
    token_type: str  # "access" | "refresh"
    family: str | None = None  # refresh token rotation family


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class JWTHandler:
    def __init__(
        self,
        private_key: str,
        public_key: str,
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 30,
    ) -> None:
        self._private_key = private_key
        self._public_key = public_key
        self._access_expire = access_token_expire_minutes
        self._refresh_expire = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        roles: list[str],
        permissions: list[str],
    ) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "roles": roles,
            "permissions": permissions,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self._access_expire)).timestamp()),
            "jti": str(uuid.uuid4()),
            "token_type": "access",
        }
        return jwt.encode(payload, self._private_key, algorithm=ALGORITHM)

    def create_refresh_token(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        family: uuid.UUID | None = None,
    ) -> tuple[str, str]:
        """Returns (raw_token, token_hash). Store only the hash."""
        now = datetime.now(UTC)
        raw = secrets.token_urlsafe(64)
        token_family = str(family) if family else str(uuid.uuid4())
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=self._refresh_expire)).timestamp()),
            "jti": str(uuid.uuid4()),
            "token_type": "refresh",
            "family": token_family,
            "raw_ref": raw[:8],  # short non-secret ref for DB lookup
        }
        token = jwt.encode(payload, self._private_key, algorithm=ALGORITHM)
        token_hash = self._hash_token(token)
        return token, token_hash

    def decode_access_token(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(token, self._public_key, algorithms=[ALGORITHM])
        except JWTError as e:
            raise AuthenticationError(f"Invalid or expired token: {e}") from e
        if payload.get("token_type") != "access":
            raise AuthenticationError("Expected access token")
        return TokenClaims(**payload)

    def decode_refresh_token(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(token, self._public_key, algorithms=[ALGORITHM])
        except JWTError as e:
            raise AuthenticationError(f"Invalid or expired refresh token: {e}") from e
        if payload.get("token_type") != "refresh":
            raise AuthenticationError("Expected refresh token")
        return TokenClaims(**payload)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    # Backwards-compat alias
    _hash_token = hash_token
