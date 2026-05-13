from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.apps.credit_tab.models import CreditStatus
from app.apps.idempotency.schemas import IdempotencyKeySchema


class CreditTabCreate(BaseModel):
    student_id: int
    vendor_id: int
    order_id: int
    total_amount: float = Field(..., gt=0)
    due_date: datetime | None = None


class CreditPaymentCreate(IdempotencyKeySchema):
    credit_tab_id: int
    amount_paid: float = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1, max_length=100)
    note: str | None = None


class CreditPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    credit_tab_id: int
    amount_paid: float
    payment_method: str
    idempotency_key: str
    paid_at: datetime
    note: str | None


class CreditTabResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    vendor_id: int
    order_id: int
    total_amount: float
    amount_paid: float
    outstanding_balance: float
    status: CreditStatus
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class CreditTabDetailResponse(CreditTabResponse):
    payments: list[CreditPaymentResponse]


class DebtReminderSummary(BaseModel):
    total_tabs: int
    total_outstanding: float
    currency: str = "KES"
