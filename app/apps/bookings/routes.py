from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.apps.bookings.providers import provide_booking_service
from app.apps.bookings.schemas import BookingCreate, BookingResponse, BookingStatusUpdate
from app.apps.bookings.service import BookingService
from app.core.database import get_db
from app.shared.auth import AuthenticatedUser, get_current_user, require_vendor


router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("", response_model=BookingResponse)
def create_booking(
    data: BookingCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[BookingService, Depends(provide_booking_service)],
) -> BookingResponse:
    return service.create_booking(db, current_user, data)


@router.get("/me", response_model=list[BookingResponse])
def get_my_bookings(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[BookingService, Depends(provide_booking_service)],
) -> list[BookingResponse]:
    return service.fetch_my_bookings(db, current_user)


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[BookingService, Depends(provide_booking_service)],
) -> BookingResponse:
    return service.fetch_booking(db, current_user, booking_id)


@router.patch("/{booking_id}/status", response_model=BookingResponse, dependencies=[Depends(require_vendor)])
def update_booking_status(
    booking_id: int,
    data: BookingStatusUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[BookingService, Depends(provide_booking_service)],
) -> BookingResponse:
    return service.update_status(db, current_user, booking_id, data)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[BookingService, Depends(provide_booking_service)],
) -> BookingResponse:
    return service.cancel_booking(db, current_user, booking_id)
