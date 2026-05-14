from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.apps.idempotency.schemas import IdempotencyKeySchema
from app.apps.payments.models import PaymentMethod, PaymentStatus


class PaymentCreate(IdempotencyKeySchema):
    order_id: int
    method: PaymentMethod
    provider_reference: str | None = Field(default=None, max_length=255)


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus
    provider_reference: str | None = Field(default=None, max_length=255)
    failure_reason: str | None = Field(default=None, max_length=500)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    student_id: int
    amount: float
    method: PaymentMethod
    status: PaymentStatus
    idempotency_key: str
    provider_reference: str | None
    failure_reason: str | None
    paid_at: datetime | None
    created_at: datetime
