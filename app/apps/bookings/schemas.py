from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.apps.bookings.models import BookingStatus


class BookingItemCreate(BaseModel):
    service_item_id: int
    wash_type_id: int | None = None
    quantity: int = Field(..., gt=0)
    notes: str | None = Field(default=None, max_length=500)


class BookingCreate(BaseModel):
    pickup_address: str = Field(..., min_length=5, max_length=500)
    delivery_address: str | None = Field(default=None, max_length=500)
    pickup_at: datetime
    notes: str | None = Field(default=None, max_length=1000)
    items: list[BookingItemCreate] = Field(..., min_length=1)


class BookingStatusUpdate(BaseModel):
    status: BookingStatus
    vendor_id: int | None = None


class BookingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_item_id: int
    wash_type_id: int | None
    quantity: int
    unit_price: float
    line_total: float
    notes: str | None


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    vendor_id: int | None
    status: BookingStatus
    pickup_address: str
    delivery_address: str | None
    pickup_at: datetime
    notes: str | None
    total_amount: float
    items: list[BookingItemResponse]
    created_at: datetime
