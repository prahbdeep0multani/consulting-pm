import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from shared.core.exceptions import AuthorizationError, NotFoundError, UnprocessableError
from shared.core.models.base import get_current_tenant_id
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..dependencies import get_current_tenant_id_dep, get_user_roles
from ..models.billing import BillingRate, Invoice, InvoiceLineItem
from ..schemas.billing import (
    BillingRateCreate,
    BillingRateResponse,
    InvoiceCreate,
    InvoiceLineItemCreate,
    InvoiceLineItemResponse,
    InvoiceResponse,
    RecordPaymentRequest,
)

router = APIRouter(tags=["billing"])

_invoice_counter: dict[str, int] = {}


def _next_invoice_number(tenant_id: uuid.UUID) -> str:
    year = date.today().year
    key = f"{tenant_id}:{year}"
    _invoice_counter[key] = _invoice_counter.get(key, 0) + 1
    return f"INV-{year}-{_invoice_counter[key]:04d}"


def _recalculate_totals(invoice: Invoice) -> None:
    subtotal = sum(item.amount for item in invoice.line_items)
    tax = subtotal * invoice.tax_rate
    invoice.subtotal = subtotal
    invoice.tax_amount = tax.quantize(Decimal("0.01"))
    invoice.total_amount = (subtotal + tax - invoice.discount_amount).quantize(Decimal("0.01"))


# ── Billing Rates ─────────────────────────────────────────────────────────────


@router.get("/billing-rates", response_model=list[BillingRateResponse])
async def list_rates(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> list[Any]:
    result = await session.execute(
        select(BillingRate).where(
            BillingRate.tenant_id == get_current_tenant_id(), BillingRate.is_active
        )
    )
    return list(result.scalars().all())


@router.post("/billing-rates", response_model=BillingRateResponse, status_code=201)
async def create_rate(
    body: BillingRateCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin"}):
        raise AuthorizationError("Admin role required")
    rate = BillingRate(tenant_id=get_current_tenant_id(), **body.model_dump())
    session.add(rate)
    await session.commit()
    return rate


# ── Invoices ─────────────────────────────────────────────────────────────────


@router.get("/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    status: str | None = None,
    client_id: uuid.UUID | None = None,
) -> list[Any]:
    q = select(Invoice).where(
        Invoice.tenant_id == get_current_tenant_id(), Invoice.deleted_at.is_(None)
    )
    if status:
        q = q.where(Invoice.status == status)
    if client_id:
        q = q.where(Invoice.client_id == client_id)
    result = await session.execute(q.order_by(Invoice.issue_date.desc()))
    return list(result.scalars().all())


@router.post("/invoices", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    tid: Annotated[uuid.UUID, Depends(get_current_tenant_id_dep)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Manager or admin role required")
    inv = Invoice(
        tenant_id=get_current_tenant_id(),
        invoice_number=_next_invoice_number(tid),
        **body.model_dump(),
    )
    session.add(inv)
    await session.commit()
    return inv


@router.get("/invoices/{inv_id}", response_model=InvoiceResponse)
async def get_invoice(
    inv_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    result = await session.execute(
        select(Invoice).where(
            Invoice.id == inv_id,
            Invoice.tenant_id == get_current_tenant_id(),
            Invoice.deleted_at.is_(None),
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise NotFoundError("Invoice not found")
    return inv


@router.post(
    "/invoices/{inv_id}/add-line-item",
    response_model=InvoiceLineItemResponse,
    status_code=201,
)
async def add_line_item(
    inv_id: uuid.UUID,
    body: InvoiceLineItemCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
) -> object:
    result = await session.execute(
        select(Invoice).where(
            Invoice.id == inv_id,
            Invoice.tenant_id == get_current_tenant_id(),
            Invoice.deleted_at.is_(None),
        )
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise NotFoundError("Invoice not found")
    if inv.status != "draft":
        raise UnprocessableError("Can only add items to draft invoices")

    amount = (body.quantity * body.unit_price).quantize(Decimal("0.01"))
    item = InvoiceLineItem(
        tenant_id=get_current_tenant_id(),
        invoice_id=inv_id,
        amount=amount,
        sort_order=len(inv.line_items),
        **body.model_dump(),
    )
    session.add(item)
    inv.line_items.append(item)
    _recalculate_totals(inv)
    await session.commit()
    return item


@router.post("/invoices/{inv_id}/send", response_model=InvoiceResponse)
async def send_invoice(
    inv_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin", "project_manager"}):
        raise AuthorizationError("Manager or admin role required")
    result = await session.execute(
        select(Invoice).where(Invoice.id == inv_id, Invoice.tenant_id == get_current_tenant_id())
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise NotFoundError("Invoice not found")
    if inv.status != "draft":
        raise UnprocessableError("Only draft invoices can be sent")
    inv.status = "sent"
    await session.commit()
    return inv


@router.post("/invoices/{inv_id}/record-payment", response_model=InvoiceResponse)
async def record_payment(
    inv_id: uuid.UUID,
    body: RecordPaymentRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin"}):
        raise AuthorizationError("Admin role required")
    result = await session.execute(
        select(Invoice).where(Invoice.id == inv_id, Invoice.tenant_id == get_current_tenant_id())
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise NotFoundError("Invoice not found")
    inv.paid_amount = body.paid_amount
    inv.paid_at = body.paid_at or datetime.now(UTC)
    inv.status = "paid" if body.paid_amount >= inv.total_amount else "partially_paid"
    await session.commit()
    return inv


@router.post("/invoices/{inv_id}/void", response_model=InvoiceResponse)
async def void_invoice(
    inv_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[None, Depends(get_current_tenant_id_dep)],
    roles: Annotated[set[str], Depends(get_user_roles)],
) -> object:
    if not roles.intersection({"tenant_admin"}):
        raise AuthorizationError("Admin role required")
    result = await session.execute(
        select(Invoice).where(Invoice.id == inv_id, Invoice.tenant_id == get_current_tenant_id())
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise NotFoundError("Invoice not found")
    inv.status = "void"
    await session.commit()
    return inv
