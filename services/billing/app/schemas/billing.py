import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import Field

from shared.core.schemas.base import BaseSchema, TimestampSchema


class BillingRateCreate(BaseSchema):
    name: str
    type: str  # user|role|project|global
    target_id: uuid.UUID | None = None
    currency: str = "USD"
    hourly_rate: Decimal = Field(gt=0)
    effective_from: date
    effective_to: date | None = None


class BillingRateResponse(TimestampSchema):
    tenant_id: uuid.UUID
    name: str
    type: str
    target_id: uuid.UUID | None
    currency: str
    hourly_rate: Decimal
    effective_from: date
    effective_to: date | None
    is_active: bool


class InvoiceLineItemCreate(BaseSchema):
    description: str
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    is_billable: bool = True
    time_entry_id: uuid.UUID | None = None


class InvoiceLineItemResponse(BaseSchema):
    id: uuid.UUID
    invoice_id: uuid.UUID
    time_entry_id: uuid.UUID | None
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    is_billable: bool
    sort_order: int
    created_at: datetime


class InvoiceCreate(BaseSchema):
    client_id: uuid.UUID
    project_id: uuid.UUID | None = None
    issue_date: date
    due_date: date
    currency: str = "USD"
    tax_rate: Decimal = Decimal("0")
    notes: str | None = None
    payment_terms: str | None = None
    period_start: date | None = None
    period_end: date | None = None


class InvoiceResponse(TimestampSchema):
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    project_id: uuid.UUID | None
    invoice_number: str
    status: str
    issue_date: date
    due_date: date
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    currency: str
    paid_at: datetime | None
    paid_amount: Decimal | None
    line_items: list[InvoiceLineItemResponse] = []


class RecordPaymentRequest(BaseSchema):
    paid_amount: Decimal = Field(gt=0)
    paid_at: datetime | None = None
