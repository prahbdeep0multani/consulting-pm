import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_tenant_id_dep, get_current_user_id
from ..models.notification import NotificationPreference
from ..schemas.notification import NotificationPreferenceResponse, NotificationPreferenceUpdate
from shared.core.models.base import get_current_tenant_id

router = APIRouter(prefix="/preferences", tags=["preferences"])


async def _get_or_create_prefs(
    session: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> NotificationPreference:
    prefs = await session.scalar(
        select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id,
        )
    )
    if not prefs:
        prefs = NotificationPreference(tenant_id=tenant_id, user_id=user_id)
        session.add(prefs)
        await session.flush()
    return prefs


@router.get("", response_model=NotificationPreferenceResponse)
async def get_preferences(
    user_id: uuid.UUID = Depends(get_current_user_id),
    _tenant: uuid.UUID = Depends(get_current_tenant_id_dep),
    session: AsyncSession = Depends(get_session),
) -> NotificationPreferenceResponse:
    tenant_id = get_current_tenant_id()
    prefs = await _get_or_create_prefs(session, tenant_id, user_id)
    await session.commit()
    await session.refresh(prefs)
    return NotificationPreferenceResponse.model_validate(prefs)


@router.put("", response_model=NotificationPreferenceResponse)
async def replace_preferences(
    body: NotificationPreferenceUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    _tenant: uuid.UUID = Depends(get_current_tenant_id_dep),
    session: AsyncSession = Depends(get_session),
) -> NotificationPreferenceResponse:
    tenant_id = get_current_tenant_id()
    prefs = await _get_or_create_prefs(session, tenant_id, user_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    prefs.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(prefs)
    return NotificationPreferenceResponse.model_validate(prefs)


@router.patch("", response_model=NotificationPreferenceResponse)
async def update_preferences(
    body: NotificationPreferenceUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    _tenant: uuid.UUID = Depends(get_current_tenant_id_dep),
    session: AsyncSession = Depends(get_session),
) -> NotificationPreferenceResponse:
    tenant_id = get_current_tenant_id()
    prefs = await _get_or_create_prefs(session, tenant_id, user_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    prefs.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(prefs)
    return NotificationPreferenceResponse.model_validate(prefs)
