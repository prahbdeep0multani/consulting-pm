import uuid
from datetime import date, datetime

from .base import BaseEvent


class InvoiceCreatedEvent(BaseEvent):
    event_type: str = "invoice.created"
    source_service: str = "billing"
    invoice_id: uuid.UUID
    invoice_number: str
    client_id: uuid.UUID
    project_id: uuid.UUID | None
    total_amount: str
    currency: str
    due_date: date


class InvoiceSentEvent(BaseEvent):
    event_type: str = "invoice.sent"
    source_service: str = "billing"
    invoice_id: uuid.UUID
    invoice_number: str
    client_email: str
    total_amount: str
    due_date: date


class InvoicePaidEvent(BaseEvent):
    event_type: str = "invoice.paid"
    source_service: str = "billing"
    invoice_id: uuid.UUID
    invoice_number: str
    paid_amount: str
    paid_at: datetime


class InvoiceOverdueEvent(BaseEvent):
    event_type: str = "invoice.overdue"
    source_service: str = "billing"
    invoice_id: uuid.UUID
    invoice_number: str
    client_id: uuid.UUID
    total_amount: str
    days_overdue: int
