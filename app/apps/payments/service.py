from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.bookings.models import BookingStatus
from app.apps.payments.models import PaymentStatus
from app.apps.payments.repository import PaymentRepository
from app.apps.payments.schemas import PaymentCreate, PaymentResponse, PaymentStatusUpdate
from app.apps.users.models import RoleEnum, User


class PaymentService:
    def __init__(self, repository: PaymentRepository) -> None:
        self.repository = repository

    def create_payment(self, db: Session, current_user: User, data: PaymentCreate) -> PaymentResponse:
        booking = self.repository.get_booking(db, data.booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        if booking.customer_id != current_user.id and current_user.role != RoleEnum.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Booking is not available")
        if booking.status == BookingStatus.cancelled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled bookings cannot be paid")

        payment = self.repository.create_payment(
            db,
            booking_id=booking.id,
            customer_id=booking.customer_id,
            amount=booking.total_amount,
            method=data.method,
            provider_reference=data.provider_reference,
        )
        return PaymentResponse.model_validate(payment)

    def fetch_my_payments(self, db: Session, current_user: User) -> list[PaymentResponse]:
        payments = self.repository.list_for_customer(db, current_user.id)
        return [PaymentResponse.model_validate(payment) for payment in payments]

    def update_payment_status(self, db: Session, payment_id: int, data: PaymentStatusUpdate) -> PaymentResponse:
        payment = self.repository.get_by_id(db, payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

        if payment.status in {PaymentStatus.paid, PaymentStatus.refunded} and data.status != PaymentStatus.refunded:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment status cannot be changed")

        updated_payment = self.repository.update_status(
            db,
            payment,
            status=data.status,
            provider_reference=data.provider_reference,
            failure_reason=data.failure_reason,
        )
        return PaymentResponse.model_validate(updated_payment)
