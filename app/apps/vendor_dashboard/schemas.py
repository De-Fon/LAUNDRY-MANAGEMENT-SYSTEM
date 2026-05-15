from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.apps.order_management.models import OrderStatus


class VendorProfileCreate(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str
    location: str
    opening_time: str
    closing_time: str
    max_orders_per_day: int = Field(default=20, gt=0)


class VendorProfileUpdate(BaseModel):
    business_name: str | None = Field(default=None, min_length=2, max_length=100)
    phone_number: str | None = None
    location: str | None = None
    opening_time: str | None = None
    closing_time: str | None = None
    max_orders_per_day: int | None = Field(default=None, gt=0)
    is_open: bool | None = None


class VendorProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    business_name: str
    phone_number: str
    location: str
    opening_time: str
    closing_time: str
    max_orders_per_day: int
    is_open: bool
    created_at: datetime
    updated_at: datetime


class VendorCapacityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    date: date
    total_slots: int
    booked_slots: int
    available_slots: int


class OrderSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_code: str
    student_id: int
    service_item_id: int
    wash_type: str
    quantity: int
    total_price: float
    status: OrderStatus
    created_at: datetime


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendor_id: int
    business_name: str
    is_open: bool
    date: date
    total_orders_today: int
    queued: int
    washing: int
    drying: int
    ready: int
    waiting_to_pick: int
    picked_up: int
    total_revenue_today: float
    available_slots: int
    active_orders: list[OrderSummaryResponse]


class VendorStatusUpdate(BaseModel):
    is_open: bool


class BulkStatusUpdate(BaseModel):
    order_ids: list[int] = Field(..., min_length=1)
    status: OrderStatus


class BulkStatusUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    updated_count: int
