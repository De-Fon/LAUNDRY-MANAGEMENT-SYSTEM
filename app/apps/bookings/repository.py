from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.apps.bookings.models import Booking, BookingItem, BookingStatus
from app.apps.catalog.models import ServiceItem
from app.apps.pricing.models import WashType


class BookingRepository:
    def get_by_id(self, db: Session, booking_id: int) -> Booking | None:
        statement = select(Booking).options(selectinload(Booking.items)).where(Booking.id == booking_id)
        return db.scalar(statement)

    def get_service_item(self, db: Session, service_item_id: int) -> ServiceItem | None:
        statement = select(ServiceItem).where(ServiceItem.id == service_item_id, ServiceItem.is_active.is_(True))
        return db.scalar(statement)

    def get_wash_type(self, db: Session, wash_type_id: int) -> WashType | None:
        statement = select(WashType).where(WashType.id == wash_type_id, WashType.is_active.is_(True))
        return db.scalar(statement)

    def list_for_customer(self, db: Session, customer_id: int) -> list[Booking]:
        statement = (
            select(Booking)
            .options(selectinload(Booking.items))
            .where(Booking.customer_id == customer_id)
            .order_by(Booking.created_at.desc())
        )
        return list(db.scalars(statement).all())

    def list_for_vendor(self, db: Session, vendor_id: int) -> list[Booking]:
        statement = (
            select(Booking)
            .options(selectinload(Booking.items))
            .where(Booking.vendor_id == vendor_id)
            .order_by(Booking.created_at.desc())
        )
        return list(db.scalars(statement).all())

    def create_booking(
        self,
        db: Session,
        *,
        customer_id: int,
        pickup_address: str,
        delivery_address: str | None,
        pickup_at,
        notes: str | None,
        total_amount: float,
        items: list[BookingItem],
    ) -> Booking:
        booking = Booking(
            customer_id=customer_id,
            pickup_address=pickup_address,
            delivery_address=delivery_address,
            pickup_at=pickup_at,
            notes=notes,
            total_amount=total_amount,
            items=items,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return self.get_by_id(db, booking.id) or booking

    def update_status(
        self,
        db: Session,
        booking: Booking,
        status: BookingStatus,
        vendor_id: int | None = None,
    ) -> Booking:
        booking.status = status
        if vendor_id is not None:
            booking.vendor_id = vendor_id
        db.commit()
        db.refresh(booking)
        return self.get_by_id(db, booking.id) or booking
