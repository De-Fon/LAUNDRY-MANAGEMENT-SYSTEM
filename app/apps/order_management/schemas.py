from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.apps.order_management.models import OrderStatus


class OrderCreate(BaseModel):
    vendor_id: int
    service_item_id: int
    wash_type: str = Field(..., min_length=1, max_length=100)
    quantity: int = Field(default=1, ge=1)
    special_instructions: str | None = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: str | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_code: str
    student_id: int
    vendor_id: int
    service_item_id: int
    wash_type: str
    quantity: int
    total_price: float
    special_instructions: str | None
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class OrderStatusLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    previous_status: OrderStatus | None
    new_status: OrderStatus
    changed_by: int
    changed_at: datetime
    note: str | None


class OrderDetailResponse(OrderResponse):
    status_history: list[OrderStatusLogResponse]
