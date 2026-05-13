from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.bookings.models import Booking
from app.apps.payments.models import Payment, PaymentMethod, PaymentStatus


class PaymentRepository:
    def get_booking(self, db: Session, booking_id: int) -> Booking | None:
        statement = select(Booking).where(Booking.id == booking_id)
        return db.scalar(statement)

    def get_by_id(self, db: Session, payment_id: int) -> Payment | None:
        statement = select(Payment).where(Payment.id == payment_id)
        return db.scalar(statement)

    def list_for_customer(self, db: Session, customer_id: int) -> list[Payment]:
        statement = select(Payment).where(Payment.customer_id == customer_id).order_by(Payment.created_at.desc())
        return list(db.scalars(statement).all())

    def create_payment(
        self,
        db: Session,
        *,
        booking_id: int,
        customer_id: int,
        amount: float,
        method: PaymentMethod,
        provider_reference: str | None,
    ) -> Payment:
        payment = Payment(
            booking_id=booking_id,
            customer_id=customer_id,
            amount=amount,
            method=method,
            provider_reference=provider_reference,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    def update_status(
        self,
        db: Session,
        payment: Payment,
        *,
        status: PaymentStatus,
        provider_reference: str | None = None,
        failure_reason: str | None = None,
    ) -> Payment:
        payment.status = status
        payment.failure_reason = failure_reason
        if provider_reference is not None:
            payment.provider_reference = provider_reference
        if status == PaymentStatus.paid:
            payment.paid_at = datetime.now(UTC)
        db.commit()
        db.refresh(payment)
        return payment
