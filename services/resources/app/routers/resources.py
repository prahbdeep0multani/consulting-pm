import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from shared.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from shared.core.models.base import get_current_tenant_id
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_tenant_id_dep, get_current_user_id, get_user_roles
from ..models.resource import Allocation, LeaveRequest
from ..schemas.resource import (
    AllocationCreate,
    AllocationResponse,
    AllocationUpdate,
    LeaveRequestCreate,
    LeaveRequestResponse,
    RejectLeaveRequest,
)

router = APIRouter(tags=["resources"])


async def _check_over_allocation(
    session: AsyncSession,
    user_id: uuid.UUID,
    start_date: object,
    end_date: object,
    allocation_pct: int,
    exclude_id: uuid.UUID | None = None,
) -> None:
    q = select(Allocation).where(
        Allocation.user_id == user_id,
        Allocation.tenant_id == get_current_tenant_id(),
        Allocation.deleted_at.is_(None),
        or_(
            Allocation.end_date.is_(None),
            Allocation.end_date >= start_date,
        ),
        Allocation.start_date <= (end_date or "9999-12-31"),
    )
    if exclude_id:
        q = q.where(Allocation.id != exclude_id)
    result = await session.execute(q)
    existing = list(result.scalars().all())
    total = sum(a.allocation_pct for a in existing) + allocation_pct
    if total > 100:
        raise ConflictError(f"Over-allocation: total would be {total}% (max 100%)")


@router.get("/allocations", response_model=list[AllocationResponse])
async def list_allocations(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id_filter: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> list[Any]:
    q = select(Allocation).where(
        Allocation.tenant_id == get_current_tenant_id(), Allocation.deleted_at.is_(None)
    )
    if user_id_filter:
        q = q.where(Allocation.user_id == user_id_filter)
    if project_id:
        q = q.where(Allocation.project_id == project_id)
    result = await session.execute(q)
    return list(result.scalars().all())


@router.post("/allocations", response_model=AllocationResponse, status_code=201)
async def create_allocation(
    body: AllocationCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    created_by: Annotated[uuid.UUID, Depends(get_current_user_id)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Manager or admin role required")
    await _check_over_allocation(
        session, body.user_id, body.start_date, body.end_date, body.allocation_pct
    )
    alloc = Allocation(
        tenant_id=get_current_tenant_id(), created_by=created_by, **body.model_dump()
    )
    session.add(alloc)
    await session.commit()
    return alloc


@router.get("/allocations/{alloc_id}", response_model=AllocationResponse)
async def get_allocation(
    alloc_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    result = await session.execute(
        select(Allocation).where(
            Allocation.id == alloc_id,
            Allocation.tenant_id == get_current_tenant_id(),
            Allocation.deleted_at.is_(None),
        )
    )
    alloc = result.scalar_one_or_none()
    if not alloc:
        raise NotFoundError("Allocation not found")
    return alloc


@router.patch("/allocations/{alloc_id}", response_model=AllocationResponse)
async def update_allocation(
    alloc_id: uuid.UUID,
    body: AllocationUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Manager or admin role required")
    result = await session.execute(
        select(Allocation).where(
            Allocation.id == alloc_id,
            Allocation.tenant_id == get_current_tenant_id(),
            Allocation.deleted_at.is_(None),
        )
    )
    alloc = result.scalar_one_or_none()
    if not alloc:
        raise NotFoundError("Allocation not found")
    if body.allocation_pct is not None:
        await _check_over_allocation(
            session,
            alloc.user_id,
            alloc.start_date,
            body.end_date or alloc.end_date,
            body.allocation_pct,
            exclude_id=alloc_id,
        )
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(alloc, k, v)
    await session.commit()
    return alloc


@router.delete("/allocations/{alloc_id}", status_code=204)
async def delete_allocation(
    alloc_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> None:
    if not roles.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Manager or admin role required")
    result = await session.execute(
        select(Allocation).where(
            Allocation.id == alloc_id,
            Allocation.tenant_id == get_current_tenant_id(),
            Allocation.deleted_at.is_(None),
        )
    )
    alloc = result.scalar_one_or_none()
    if not alloc:
        raise NotFoundError("Allocation not found")
    alloc.deleted_at = datetime.now(UTC)
    await session.commit()


# ── Leave Requests ────────────────────────────────────────────────────────────


@router.get("/leave-requests", response_model=list[LeaveRequestResponse])
async def list_leave_requests(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> list[Any]:
    q = select(LeaveRequest).where(LeaveRequest.tenant_id == get_current_tenant_id())
    if not roles.intersection({"tenant_admin", "project_manager"}):
        q = q.where(LeaveRequest.user_id == user_id)
    result = await session.execute(q.order_by(LeaveRequest.start_date.desc()))
    return list(result.scalars().all())


@router.post("/leave-requests", response_model=LeaveRequestResponse, status_code=201)
async def create_leave_request(
    body: LeaveRequestCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
) -> object:
    leave = LeaveRequest(tenant_id=get_current_tenant_id(), user_id=user_id, **body.model_dump())
    session.add(leave)
    await session.commit()
    return leave


@router.post("/leave-requests/{leave_id}/approve", response_model=LeaveRequestResponse)
async def approve_leave(
    leave_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Manager or admin role required")
    result = await session.execute(
        select(LeaveRequest).where(
            LeaveRequest.id == leave_id, LeaveRequest.tenant_id == get_current_tenant_id()
        )
    )
    leave = result.scalar_one_or_none()
    if not leave:
        raise NotFoundError("Leave request not found")
    leave.status = "approved"
    leave.approver_user_id = user_id
    leave.approved_at = datetime.now(UTC)
    await session.commit()
    return leave


@router.post("/leave-requests/{leave_id}/reject", response_model=LeaveRequestResponse)
async def reject_leave(
    leave_id: uuid.UUID,
    body: RejectLeaveRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    user_id: Annotated[uuid.UUID, Depends(get_current_user_id)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Manager or admin role required")
    result = await session.execute(
        select(LeaveRequest).where(
            LeaveRequest.id == leave_id, LeaveRequest.tenant_id == get_current_tenant_id()
        )
    )
    leave = result.scalar_one_or_none()
    if not leave:
        raise NotFoundError("Leave request not found")
    leave.status = "rejected"
    leave.approver_user_id = user_id
    leave.rejection_reason = body.rejection_reason
    await session.commit()
    return leave
