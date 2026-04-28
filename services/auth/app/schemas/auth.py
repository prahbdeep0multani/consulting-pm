from pydantic import EmailStr, Field
from shared.core.schemas.base import BaseSchema


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str
    tenant_slug: str


class LoginResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class RefreshRequest(BaseSchema):
    refresh_token: str
    tenant_slug: str


class RefreshResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class ForgotPasswordRequest(BaseSchema):
    email: EmailStr
    tenant_slug: str


class ResetPasswordRequest(BaseSchema):
    token: str
    new_password: str = Field(min_length=8)


class VerifyEmailRequest(BaseSchema):
    token: str


class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str = Field(min_length=8)


class MFAVerifyRequest(BaseSchema):
    code: str = Field(min_length=6, max_length=6)
