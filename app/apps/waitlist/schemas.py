from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.apps.waitlist.models import WaitlistStatus


class WaitlistEntryCreate(BaseModel):
    service_item_id: int
    note: str | None = Field(default=None, max_length=500)


class WaitlistStatusUpdate(BaseModel):
    status: WaitlistStatus


class WaitlistEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    service_item_id: int
    status: WaitlistStatus
    note: str | None
    created_at: datetime
    notified_at: datetime | None
    converted_at: datetime | None
