from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.apps.idempotency.schemas import IdempotencyKeySchema
from app.apps.payments.models import PaymentMethod, PaymentStatus


class PaymentCreate(IdempotencyKeySchema):
    order_id: int
    method: PaymentMethod
    provider_reference: str | None = Field(default=None, max_length=255)


class STKPushRequest(IdempotencyKeySchema):
    order_id: int
    phone_number: str = Field(..., min_length=9, max_length=20)


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus
    provider_reference: str | None = Field(default=None, max_length=255)
    failure_reason: str | None = Field(default=None, max_length=500)


class STKPushResponse(BaseModel):
    payment_id: int
    status: PaymentStatus
    checkout_request_id: str | None
    merchant_request_id: str | None
    customer_message: str


class STKQueryResponse(BaseModel):
    payment_id: int
    status: PaymentStatus
    checkout_request_id: str | None
    provider_result_code: str | None
    provider_result_description: str | None


class DarajaCallbackResponse(BaseModel):
    result_code: int = 0
    result_description: str = "Accepted"


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    student_id: int
    amount: float
    method: PaymentMethod
    status: PaymentStatus
    idempotency_key: str
    phone_number: str | None
    account_reference: str | None
    checkout_request_id: str | None
    merchant_request_id: str | None
    provider_reference: str | None
    provider_result_code: str | None
    provider_result_description: str | None
    failure_reason: str | None
    retry_count: int
    paid_at: datetime | None
    last_queried_at: datetime | None
    next_reconciliation_at: datetime | None
    created_at: datetime


class CallbackLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    checkout_request_id: str | None
    merchant_request_id: str | None
    result_code: int | None
    processed: bool
    error_message: str | None
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
    context: dict[str, Any] | None = None
