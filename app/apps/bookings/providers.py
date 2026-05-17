from typing import Annotated

from fastapi import Depends

from app.apps.bookings.repository import BookingRepository
from app.apps.bookings.service import BookingService
from app.apps.notifications.providers import provide_notification_service
from app.apps.notifications.service import NotificationService


def provide_booking_repository() -> BookingRepository:
    return BookingRepository()


def provide_booking_service(
    repository: Annotated[BookingRepository, Depends(provide_booking_repository)],
    notification_service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> BookingService:
    return BookingService(repository, notification_service)
