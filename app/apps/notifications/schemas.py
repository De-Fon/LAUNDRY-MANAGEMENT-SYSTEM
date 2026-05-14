from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.apps.notifications.models import NotificationChannel, NotificationStatus


class NotificationCreate(BaseModel):
    user_id: int
    channel: NotificationChannel = NotificationChannel.in_app
    subject: str = Field(..., min_length=2, max_length=200)
    message: str = Field(..., min_length=1)


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    channel: NotificationChannel
    status: NotificationStatus
    subject: str
    message: str
    sent_at: datetime | None
    read_at: datetime | None
    created_at: datetime
