from typing import Annotated

from fastapi import Depends

from app.apps.bookings.repository import BookingRepository
from app.apps.bookings.service import BookingService


def provide_booking_repository() -> BookingRepository:
    return BookingRepository()


def provide_booking_service(
    repository: Annotated[BookingRepository, Depends(provide_booking_repository)],
) -> BookingService:
    return BookingService(repository)
