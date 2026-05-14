from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.order_management.models import Order
from app.apps.payments.models import Payment, PaymentMethod, PaymentStatus


class PaymentRepository:
    def get_order(self, db: Session, order_id: int) -> Order | None:
        statement = select(Order).where(Order.id == order_id)
        return db.scalar(statement)

    def get_by_id(self, db: Session, payment_id: int) -> Payment | None:
        statement = select(Payment).where(Payment.id == payment_id)
        return db.scalar(statement)

    def list_for_customer(self, db: Session, customer_id: int) -> list[Payment]:
        statement = select(Payment).where(Payment.student_id == customer_id).order_by(Payment.created_at.desc())
        return list(db.scalars(statement).all())

    def get_by_idempotency_key(self, db: Session, idempotency_key: str) -> Payment | None:
        statement = select(Payment).where(Payment.idempotency_key == idempotency_key)
        return db.scalar(statement)

    def create_payment(
        self,
        db: Session,
        *,
        order_id: int,
        student_id: int,
        amount: float,
        method: PaymentMethod,
        idempotency_key: str,
        provider_reference: str | None,
    ) -> Payment:
        payment = Payment(
            order_id=order_id,
            student_id=student_id,
            amount=amount,
            method=method,
            idempotency_key=idempotency_key,
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
        if status == PaymentStatus.PAID:
            payment.paid_at = datetime.now(UTC)
        db.commit()
        db.refresh(payment)
        return payment
