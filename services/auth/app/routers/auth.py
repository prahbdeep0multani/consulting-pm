from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from shared.core.security.jwt import JWTHandler
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_user, get_jwt_handler
from ..models.user import User
from ..schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MFAVerifyRequest,
    RefreshRequest,
    RefreshResponse,
    ResetPasswordRequest,
)
from ..security.totp import TOTPHandler
from ..services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_client_info(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("User-Agent")
    return ip, ua


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    jwt: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> object:
    ip, ua = _get_client_info(request)
    svc = AuthService(session, jwt)
    access, refresh = await svc.login(body.tenant_slug, body.email, body.password, ip, ua)
    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=jwt._access_expire * 60,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    body: RefreshRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    jwt: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> object:
    ip, ua = _get_client_info(request)
    svc = AuthService(session, jwt)
    access, refresh = await svc.refresh(body.tenant_slug, body.refresh_token, ip, ua)
    return RefreshResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=jwt._access_expire * 60,
    )


@router.post("/logout", status_code=204)
async def logout(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    jwt: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> None:
    svc = AuthService(session, jwt)
    await svc.logout(body.refresh_token)


@router.post("/logout-all", status_code=204)
async def logout_all(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    jwt: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> None:
    svc = AuthService(session, jwt)
    await svc.logout_all(current_user.id)


@router.post("/forgot-password", status_code=202)
async def forgot_password(
    body: ForgotPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    jwt: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> dict[str, Any]:
    svc = AuthService(session, jwt)
    await svc.forgot_password(body.tenant_slug, body.email)
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password", status_code=204)
async def reset_password(
    body: ResetPasswordRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    jwt: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> None:
    svc = AuthService(session, jwt)
    await svc.reset_password(body.token, body.new_password)


@router.post("/change-password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    jwt: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> None:
    svc = AuthService(session, jwt)
    await svc.change_password(current_user, body.current_password, body.new_password)


@router.post("/mfa/enable")
async def mfa_enable(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    secret = TOTPHandler.generate_secret()
    current_user.mfa_secret = secret  # store temporarily; confirmed on /mfa/verify
    await session.commit()
    uri = TOTPHandler.get_provisioning_uri(secret, current_user.email)
    return {"provisioning_uri": uri, "qr_code": TOTPHandler.get_qr_code_data_uri(uri)}


@router.post("/mfa/verify", status_code=204)
async def mfa_verify(
    body: MFAVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    from shared.core.exceptions import AuthenticationError

    if not current_user.mfa_secret or not TOTPHandler.verify(current_user.mfa_secret, body.code):
        raise AuthenticationError("Invalid TOTP code")
    await session.commit()


@router.post("/mfa/disable", status_code=204)
async def mfa_disable(
    body: MFAVerifyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    from shared.core.exceptions import AuthenticationError

    if not current_user.mfa_secret or not TOTPHandler.verify(current_user.mfa_secret, body.code):
        raise AuthenticationError("Invalid TOTP code")
    current_user.mfa_secret = None
    await session.commit()
