from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.bookings.models import Booking, BookingItem, BookingStatus
from app.apps.bookings.repository import BookingRepository
from app.apps.bookings.schemas import BookingCreate, BookingResponse, BookingStatusUpdate
from app.apps.users.models import RoleEnum, User


class BookingService:
    def __init__(self, repository: BookingRepository) -> None:
        self.repository = repository

    def create_booking(self, db: Session, customer: User, data: BookingCreate) -> BookingResponse:
        pickup_at = data.pickup_at if data.pickup_at.tzinfo is not None else data.pickup_at.replace(tzinfo=UTC)
        if pickup_at <= datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pickup time must be in the future")

        booking_items: list[BookingItem] = []
        total_amount = 0.0
        for item_data in data.items:
            service_item = self.repository.get_service_item(db, item_data.service_item_id)
            if service_item is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")

            multiplier = 1.0
            if item_data.wash_type_id is not None:
                wash_type = self.repository.get_wash_type(db, item_data.wash_type_id)
                if wash_type is None:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wash type not found")
                multiplier = wash_type.price_multiplier

            unit_price = round(service_item.base_price * multiplier, 2)
            line_total = round(unit_price * item_data.quantity, 2)
            total_amount = round(total_amount + line_total, 2)
            booking_items.append(
                BookingItem(
                    service_item_id=item_data.service_item_id,
                    wash_type_id=item_data.wash_type_id,
                    quantity=item_data.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    notes=item_data.notes,
                )
            )

        booking = self.repository.create_booking(
            db,
            customer_id=customer.id,
            pickup_address=data.pickup_address,
            delivery_address=data.delivery_address,
            pickup_at=pickup_at,
            notes=data.notes,
            total_amount=total_amount,
            items=booking_items,
        )
        return BookingResponse.model_validate(booking)

    def fetch_booking(self, db: Session, current_user: User, booking_id: int) -> BookingResponse:
        booking = self._get_visible_booking(db, current_user, booking_id)
        return BookingResponse.model_validate(booking)

    def fetch_my_bookings(self, db: Session, current_user: User) -> list[BookingResponse]:
        if current_user.role in {RoleEnum.vendor, RoleEnum.admin}:
            bookings = self.repository.list_for_vendor(db, current_user.id)
        else:
            bookings = self.repository.list_for_customer(db, current_user.id)
        return [BookingResponse.model_validate(booking) for booking in bookings]

    def update_status(
        self,
        db: Session,
        current_user: User,
        booking_id: int,
        data: BookingStatusUpdate,
    ) -> BookingResponse:
        if current_user.role not in {RoleEnum.vendor, RoleEnum.admin}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only vendors can update bookings")

        booking = self.repository.get_by_id(db, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        vendor_id = data.vendor_id if current_user.role == RoleEnum.admin else current_user.id
        updated_booking = self.repository.update_status(db, booking, data.status, vendor_id)
        return BookingResponse.model_validate(updated_booking)

    def cancel_booking(self, db: Session, current_user: User, booking_id: int) -> BookingResponse:
        booking = self._get_visible_booking(db, current_user, booking_id)
        if booking.status in {BookingStatus.completed, BookingStatus.cancelled}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking cannot be cancelled")
        updated_booking = self.repository.update_status(db, booking, BookingStatus.cancelled)
        return BookingResponse.model_validate(updated_booking)

    def _get_visible_booking(self, db: Session, current_user: User, booking_id: int) -> Booking:
        booking = self.repository.get_by_id(db, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        can_view = current_user.role == RoleEnum.admin or booking.customer_id == current_user.id
        can_view = can_view or (booking.vendor_id is not None and booking.vendor_id == current_user.id)
        if not can_view:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Booking is not available")
        return booking
