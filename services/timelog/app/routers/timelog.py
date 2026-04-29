import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from shared.core.exceptions import AuthorizationError, NotFoundError, UnprocessableError
from shared.core.models.base import get_current_tenant_id
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_tenant_id_dep, get_current_user_id, get_user_roles
from ..models.timelog import TimeEntry, TimeEntryApproval
from ..schemas.timelog import (
    RejectRequest,
    TimeEntryCreate,
    TimeEntryResponse,
    TimeEntryUpdate,
    TimerStopRequest,
)

router = APIRouter(tags=["timelog"])


async def _get_entry(session: AsyncSession, entry_id: uuid.UUID) -> TimeEntry:
    result = await session.execute(
        select(TimeEntry).where(
            TimeEntry.id == entry_id,
            TimeEntry.tenant_id == get_current_tenant_id(),
            TimeEntry.deleted_at.is_(None),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise NotFoundError("Time entry not found")
    return entry


@router.get("/time-entries", response_model=list[TimeEntryResponse])
async def list_entries(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    project_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[Any]:
    q = select(TimeEntry).where(
        TimeEntry.user_id == user_id,
        TimeEntry.tenant_id == get_current_tenant_id(),
        TimeEntry.deleted_at.is_(None),
    )
    if project_id:
        q = q.where(TimeEntry.project_id == project_id)
    if status:
        q = q.where(TimeEntry.status == status)
    result = await session.execute(q.order_by(TimeEntry.date.desc()).limit(limit))
    return list(result.scalars().all())


@router.post("/time-entries", response_model=TimeEntryResponse, status_code=201)
async def create_entry(
    body: TimeEntryCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
) -> object:
    entry = TimeEntry(
        tenant_id=get_current_tenant_id(),
        user_id=user_id,
        **body.model_dump(),
    )
    session.add(entry)
    await session.commit()
    return entry


@router.get("/time-entries/{entry_id}", response_model=TimeEntryResponse)
async def get_entry(
    entry_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    return await _get_entry(session, entry_id)


@router.patch("/time-entries/{entry_id}", response_model=TimeEntryResponse)
async def update_entry(
    entry_id: uuid.UUID,
    body: TimeEntryUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
) -> object:
    entry = await _get_entry(session, entry_id)
    if entry.user_id != user_id:
        raise AuthorizationError("Cannot edit another user's time entry")
    if entry.status != "draft":
        raise UnprocessableError("Only draft entries can be edited")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(entry, k, v)
    await session.commit()
    return entry


@router.delete("/time-entries/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
) -> None:
    entry = await _get_entry(session, entry_id)
    if entry.user_id != user_id:
        raise AuthorizationError("Cannot delete another user's time entry")
    if entry.status != "draft":
        raise UnprocessableError("Only draft entries can be deleted")
    entry.deleted_at = datetime.now(UTC)
    await session.commit()


@router.post("/time-entries/{entry_id}/start-timer", response_model=TimeEntryResponse)
async def start_timer(
    entry_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    entry = await _get_entry(session, entry_id)
    if entry.started_at:
        raise UnprocessableError("Timer already started")
    entry.started_at = datetime.now(UTC)
    await session.commit()
    return entry


@router.post("/time-entries/{entry_id}/stop-timer", response_model=TimeEntryResponse)
async def stop_timer(
    entry_id: uuid.UUID,
    body: TimerStopRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    entry = await _get_entry(session, entry_id)
    if not entry.started_at:
        raise UnprocessableError("Timer not started")
    ended = body.ended_at or datetime.now(UTC)
    entry.ended_at = ended
    delta = ended - entry.started_at
    entry.duration_minutes = max(1, int(delta.total_seconds() / 60))
    await session.commit()
    return entry


@router.post("/time-entries/{entry_id}/submit", response_model=TimeEntryResponse)
async def submit_entry(
    entry_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
) -> object:
    entry = await _get_entry(session, entry_id)
    if entry.status != "draft":
        raise UnprocessableError("Only draft entries can be submitted")
    entry.status = "submitted"
    approval = TimeEntryApproval(
        tenant_id=get_current_tenant_id(),
        time_entry_id=entry.id,
        approver_user_id=user_id,
        action="submitted",
    )
    session.add(approval)
    await session.commit()
    return entry


@router.post("/time-entries/{entry_id}/approve", response_model=TimeEntryResponse)
async def approve_entry(
    entry_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Manager or admin role required")
    entry = await _get_entry(session, entry_id)
    if entry.status != "submitted":
        raise UnprocessableError("Only submitted entries can be approved")
    entry.status = "approved"
    approval = TimeEntryApproval(
        tenant_id=get_current_tenant_id(),
        time_entry_id=entry.id,
        approver_user_id=user_id,
        action="approved",
    )
    session.add(approval)
    await session.commit()
    return entry


@router.post("/time-entries/{entry_id}/reject", response_model=TimeEntryResponse)
async def reject_entry(
    entry_id: uuid.UUID,
    body: RejectRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Manager or admin role required")
    entry = await _get_entry(session, entry_id)
    if entry.status != "submitted":
        raise UnprocessableError("Only submitted entries can be rejected")
    entry.status = "rejected"
    approval = TimeEntryApproval(
        tenant_id=get_current_tenant_id(),
        time_entry_id=entry.id,
        approver_user_id=user_id,
        action="rejected",
        notes=body.notes,
    )
    session.add(approval)
    await session.commit()
    return entry


@router.get("/approvals/pending", response_model=list[TimeEntryResponse])
async def pending_approvals(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> list[Any]:
    if not roles.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Manager or admin role required")
    result = await session.execute(
        select(TimeEntry).where(
            TimeEntry.tenant_id == get_current_tenant_id(),
            TimeEntry.status == "submitted",
            TimeEntry.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())
