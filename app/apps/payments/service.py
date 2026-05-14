from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.idempotency.service import IdempotencyService
from app.apps.order_management.models import OrderStatus
from app.apps.payments.models import Payment, PaymentStatus
from app.apps.payments.repository import PaymentRepository
from app.apps.payments.schemas import PaymentCreate, PaymentResponse, PaymentStatusUpdate
from app.apps.users.models import RoleEnum, User


class PaymentService:
    def __init__(self, repository: PaymentRepository, idempotency_service: IdempotencyService) -> None:
        self.repository = repository
        self.idempotency_service = idempotency_service

    def create_payment(self, db: Session, current_user: User, data: PaymentCreate) -> PaymentResponse:
        duplicate = self.idempotency_service.find_duplicate(db, Payment, data.idempotency_key)
        if duplicate is not None:
            self.idempotency_service.log_duplicate(data.idempotency_key, "PAYMENT", current_user.id)
            return PaymentResponse.model_validate(duplicate)

        order = self.repository.get_order(db, data.order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.student_id != current_user.id and current_user.role != RoleEnum.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Order is not available")
        if order.status == OrderStatus.CANCELLED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled orders cannot be paid")

        payment = self.repository.create_payment(
            db,
            order_id=order.id,
            student_id=order.student_id,
            amount=order.total_price,
            method=data.method,
            idempotency_key=data.idempotency_key,
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

        if payment.status in {PaymentStatus.PAID, PaymentStatus.REFUNDED} and data.status != PaymentStatus.REFUNDED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment status cannot be changed")

        updated_payment = self.repository.update_status(
            db,
            payment,
            status=data.status,
            provider_reference=data.provider_reference,
            failure_reason=data.failure_reason,
        )
        return PaymentResponse.model_validate(updated_payment)
