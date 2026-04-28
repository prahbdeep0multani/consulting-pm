import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from shared.core.models.base import get_current_tenant_id
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_tenant_id_dep, get_current_user_id
from ..models.notification import Notification
from ..schemas.notification import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    user_id: uuid.UUID = Depends(get_current_user_id),
    _tenant: uuid.UUID = Depends(get_current_tenant_id_dep),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationResponse]:
    tenant_id = get_current_tenant_id()
    stmt = (
        select(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.recipient_user_id == user_id,
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    result = await session.execute(stmt)
    return [NotificationResponse.model_validate(n) for n in result.scalars().all()]


@router.get("/unread-count")
async def unread_count(
    user_id: uuid.UUID = Depends(get_current_user_id),
    _tenant: uuid.UUID = Depends(get_current_tenant_id_dep),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    tenant_id = get_current_tenant_id()
    stmt = select(func.count()).where(
        Notification.tenant_id == tenant_id,
        Notification.recipient_user_id == user_id,
        Notification.is_read.is_(False),
    )
    count = await session.scalar(stmt) or 0
    return {"count": count}


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    _tenant: uuid.UUID = Depends(get_current_tenant_id_dep),
    session: AsyncSession = Depends(get_session),
) -> NotificationResponse:
    tenant_id = get_current_tenant_id()
    n = await session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.tenant_id == tenant_id,
            Notification.recipient_user_id == user_id,
        )
    )
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationResponse.model_validate(n)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    _tenant: uuid.UUID = Depends(get_current_tenant_id_dep),
    session: AsyncSession = Depends(get_session),
) -> NotificationResponse:
    tenant_id = get_current_tenant_id()
    n = await session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.tenant_id == tenant_id,
            Notification.recipient_user_id == user_id,
        )
    )
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if not n.is_read:
        n.is_read = True
        n.read_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(n)
    return NotificationResponse.model_validate(n)


@router.post("/read-all")
async def mark_all_read(
    user_id: uuid.UUID = Depends(get_current_user_id),
    _tenant: uuid.UUID = Depends(get_current_tenant_id_dep),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    tenant_id = get_current_tenant_id()
    now = datetime.now(UTC)
    await session.execute(
        update(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.recipient_user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=now)
    )
    await session.commit()
    return {"status": "ok"}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    _tenant: uuid.UUID = Depends(get_current_tenant_id_dep),
    session: AsyncSession = Depends(get_session),
) -> None:
    tenant_id = get_current_tenant_id()
    n = await session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.tenant_id == tenant_id,
            Notification.recipient_user_id == user_id,
        )
    )
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await session.delete(n)
    await session.commit()
