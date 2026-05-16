from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.apps.order_management.models import Order
from app.apps.payments.models import (
    CallbackLog,
    Payment,
    PaymentAttempt,
    PaymentAttemptStatus,
    PaymentMethod,
    PaymentStatus,
    PaymentStatusHistory,
    Transaction,
    TransactionType,
)


class PaymentRepository:
    def get_order(self, db: Session, order_id: int) -> Order | None:
        statement = select(Order).where(Order.id == order_id)
        return db.scalar(statement)

    def get_by_id(self, db: Session, payment_id: int) -> Payment | None:
        statement = (
            select(Payment)
            .options(selectinload(Payment.attempts), selectinload(Payment.status_history))
            .where(Payment.id == payment_id)
        )
        return db.scalar(statement)

    def get_by_checkout_request_id(self, db: Session, checkout_request_id: str) -> Payment | None:
        statement = select(Payment).where(Payment.checkout_request_id == checkout_request_id)
        return db.scalar(statement)

    def list_for_customer(self, db: Session, customer_id: int) -> list[Payment]:
        statement = select(Payment).where(Payment.student_id == customer_id).order_by(Payment.created_at.desc())
        return list(db.scalars(statement).all())

    def get_by_idempotency_key(self, db: Session, idempotency_key: str) -> Payment | None:
        statement = select(Payment).where(Payment.idempotency_key == idempotency_key)
        return db.scalar(statement)

    def list_due_for_reconciliation(self, db: Session, *, now: datetime, limit: int) -> list[Payment]:
        statement = (
            select(Payment)
            .where(
                Payment.method == PaymentMethod.MPESA,
                Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.PROCESSING]),
                Payment.checkout_request_id.is_not(None),
                Payment.next_reconciliation_at.is_not(None),
                Payment.next_reconciliation_at <= now,
            )
            .order_by(Payment.next_reconciliation_at.asc())
            .limit(limit)
        )
        return list(db.scalars(statement).all())

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
        phone_number: str | None = None,
        account_reference: str | None = None,
    ) -> Payment:
        payment = Payment(
            order_id=order_id,
            student_id=student_id,
            amount=amount,
            method=method,
            idempotency_key=idempotency_key,
            provider_reference=provider_reference,
            phone_number=phone_number,
            account_reference=account_reference,
        )
        db.add(payment)
        db.flush()
        self.add_status_history(db, payment=payment, from_status=None, to_status=payment.status, reason="Payment created")
        return payment

    def create_payment_attempt(
        self,
        db: Session,
        *,
        payment: Payment,
        attempt_number: int,
        request_payload: dict[str, Any] | None = None,
    ) -> PaymentAttempt:
        attempt = PaymentAttempt(
            payment_id=payment.id,
            attempt_number=attempt_number,
            request_payload=request_payload,
        )
        db.add(attempt)
        db.flush()
        return attempt

    def update_attempt(
        self,
        attempt: PaymentAttempt,
        *,
        status: PaymentAttemptStatus,
        response_payload: dict[str, Any] | None = None,
        checkout_request_id: str | None = None,
        merchant_request_id: str | None = None,
        error_message: str | None = None,
    ) -> PaymentAttempt:
        attempt.status = status
        attempt.response_payload = response_payload
        attempt.checkout_request_id = checkout_request_id
        attempt.merchant_request_id = merchant_request_id
        attempt.error_message = error_message
        return attempt

    def update_status(
        self,
        db: Session,
        payment: Payment,
        *,
        status: PaymentStatus,
        reason: str,
        provider_reference: str | None = None,
        provider_result_code: str | None = None,
        provider_result_description: str | None = None,
        failure_reason: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        changed_by_id: int | None = None,
    ) -> Payment:
        old_status = payment.status
        payment.status = status
        payment.provider_result_code = provider_result_code
        payment.provider_result_description = provider_result_description
        payment.failure_reason = failure_reason
        if provider_reference is not None:
            payment.provider_reference = provider_reference
        if status == PaymentStatus.SUCCESS:
            payment.paid_at = datetime.now(UTC)
            payment.next_reconciliation_at = None
        if status in {PaymentStatus.FAILED, PaymentStatus.CANCELLED, PaymentStatus.TIMEOUT, PaymentStatus.REVERSED}:
            payment.next_reconciliation_at = None
        self.add_status_history(
            db,
            payment=payment,
            from_status=old_status,
            to_status=status,
            reason=reason,
            metadata_json=metadata_json,
            changed_by_id=changed_by_id,
        )
        db.flush()
        return payment

    def mark_stk_accepted(
        self,
        payment: Payment,
        *,
        checkout_request_id: str,
        merchant_request_id: str,
        next_reconciliation_at: datetime,
    ) -> Payment:
        payment.checkout_request_id = checkout_request_id
        payment.merchant_request_id = merchant_request_id
        payment.status = PaymentStatus.PROCESSING
        payment.next_reconciliation_at = next_reconciliation_at
        return payment

    def mark_query_attempt(self, payment: Payment, *, queried_at: datetime, next_reconciliation_at: datetime | None) -> None:
        payment.retry_count += 1
        payment.last_queried_at = queried_at
        payment.next_reconciliation_at = next_reconciliation_at

    def create_transaction(
        self,
        db: Session,
        *,
        payment: Payment,
        transaction_type: TransactionType,
        provider_transaction_id: str | None,
        amount: float | None,
        phone_number: str | None,
        raw_payload: dict[str, Any] | None,
        occurred_at: datetime | None,
    ) -> Transaction:
        transaction = Transaction(
            payment_id=payment.id,
            transaction_type=transaction_type,
            provider_transaction_id=provider_transaction_id,
            amount=amount,
            phone_number=phone_number,
            raw_payload=raw_payload,
            occurred_at=occurred_at,
        )
        db.add(transaction)
        db.flush()
        return transaction

    def create_callback_log(
        self,
        db: Session,
        *,
        checkout_request_id: str | None,
        merchant_request_id: str | None,
        result_code: int | None,
        payload_hash: str,
        raw_payload: dict[str, Any],
    ) -> CallbackLog:
        callback_log = CallbackLog(
            checkout_request_id=checkout_request_id,
            merchant_request_id=merchant_request_id,
            result_code=result_code,
            payload_hash=payload_hash,
            raw_payload=raw_payload,
        )
        db.add(callback_log)
        db.flush()
        return callback_log

    def get_callback_by_hash(self, db: Session, payload_hash: str) -> CallbackLog | None:
        statement = select(CallbackLog).where(CallbackLog.payload_hash == payload_hash)
        return db.scalar(statement)

    def mark_callback_processed(self, callback_log: CallbackLog) -> None:
        callback_log.processed = True
        callback_log.error_message = None

    def mark_callback_failed(self, callback_log: CallbackLog, error_message: str) -> None:
        callback_log.processed = False
        callback_log.error_message = error_message[:500]

    def add_status_history(
        self,
        db: Session,
        *,
        payment: Payment,
        from_status: PaymentStatus | None,
        to_status: PaymentStatus,
        reason: str,
        metadata_json: dict[str, Any] | None = None,
        changed_by_id: int | None = None,
    ) -> PaymentStatusHistory:
        status_history = PaymentStatusHistory(
            payment_id=payment.id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            metadata_json=metadata_json,
            changed_by_id=changed_by_id,
        )
        db.add(status_history)
        db.flush()
        return status_history
