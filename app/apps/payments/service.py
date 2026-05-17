from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.apps.idempotency.service import IdempotencyService
from app.apps.notifications.service import NotificationService
from app.apps.order_management.models import OrderStatus
from app.apps.payments.models import (
    Payment,
    PaymentAttemptStatus,
    PaymentMethod,
    PaymentStatus,
    TransactionType,
)
from app.apps.payments.repository import PaymentRepository
from app.apps.payments.schemas import (
    DarajaCallbackResponse,
    PaymentCreate,
    PaymentResponse,
    PaymentStatusUpdate,
    STKPushRequest,
    STKPushResponse,
    STKQueryResponse,
)
from app.apps.users.models import RoleEnum, User
from app.core.settings import Settings
from app.integrations.daraja.client import DarajaAPIError, DarajaClient
from app.utils.phone import normalize_kenyan_msisdn


TERMINAL_STATUSES = {
    PaymentStatus.SUCCESS,
    PaymentStatus.FAILED,
    PaymentStatus.CANCELLED,
    PaymentStatus.TIMEOUT,
    PaymentStatus.REVERSED,
}

ALLOWED_TRANSITIONS = {
    PaymentStatus.PENDING: {PaymentStatus.PROCESSING, PaymentStatus.FAILED, PaymentStatus.CANCELLED, PaymentStatus.TIMEOUT},
    PaymentStatus.PROCESSING: {
        PaymentStatus.SUCCESS,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELLED,
        PaymentStatus.TIMEOUT,
        PaymentStatus.REVERSED,
    },
    PaymentStatus.SUCCESS: {PaymentStatus.REVERSED},
    PaymentStatus.FAILED: set(),
    PaymentStatus.CANCELLED: set(),
    PaymentStatus.TIMEOUT: set(),
    PaymentStatus.REVERSED: set(),
}

SUCCESS_RESULT_CODES = {"0"}
CANCELLED_RESULT_CODES = {"1032"}
TIMEOUT_RESULT_CODES = {"1037", "1001"}


class PaymentService:
    def __init__(
        self,
        repository: PaymentRepository,
        idempotency_service: IdempotencyService,
        daraja_client: DarajaClient,
        settings: Settings,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.repository = repository
        self.idempotency_service = idempotency_service
        self.daraja_client = daraja_client
        self.settings = settings
        self.notification_service = notification_service

    def create_payment(self, db: Session, current_user: User, data: PaymentCreate) -> PaymentResponse:
        duplicate = self.idempotency_service.find_duplicate(db, Payment, data.idempotency_key)
        if duplicate is not None:
            self.idempotency_service.log_duplicate(data.idempotency_key, "PAYMENT", current_user.id)
            return PaymentResponse.model_validate(duplicate)

        order = self._get_payable_order(db, current_user, data.order_id)
        payment = self.repository.create_payment(
            db,
            order_id=order.id,
            student_id=order.student_id,
            amount=order.total_price,
            method=data.method,
            idempotency_key=data.idempotency_key,
            provider_reference=data.provider_reference,
        )
        db.commit()
        db.refresh(payment)
        return PaymentResponse.model_validate(payment)

    def initiate_stk_push(self, db: Session, current_user: User, data: STKPushRequest) -> STKPushResponse:
        duplicate = self.idempotency_service.find_duplicate(db, Payment, data.idempotency_key)
        if duplicate is not None:
            self.idempotency_service.log_duplicate(data.idempotency_key, "MPESA_STK_PUSH", current_user.id)
            return self._stk_response(duplicate, "Duplicate request reused")

        if not self.settings.daraja_callback_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Daraja callback URL is not configured",
            )

        order = self._get_payable_order(db, current_user, data.order_id)
        phone_number = normalize_kenyan_msisdn(data.phone_number)
        account_reference = f"{self.settings.daraja_account_reference_prefix}-{order.id}"
        amount = max(1, int(round(order.total_price)))

        payment = self.repository.create_payment(
            db,
            order_id=order.id,
            student_id=order.student_id,
            amount=order.total_price,
            method=PaymentMethod.MPESA,
            idempotency_key=data.idempotency_key,
            provider_reference=None,
            phone_number=phone_number,
            account_reference=account_reference,
        )
        attempt = self.repository.create_payment_attempt(
            db,
            payment=payment,
            attempt_number=1,
            request_payload={"phone_number": phone_number, "amount": amount, "account_reference": account_reference},
        )

        try:
            response_payload = self.daraja_client.initiate_stk_push(
                phone_number=phone_number,
                amount=amount,
                account_reference=account_reference,
                transaction_desc=self.settings.daraja_transaction_desc,
                callback_url=self.settings.daraja_callback_url,
            )
        except DarajaAPIError as exc:
            self.repository.update_attempt(
                attempt,
                status=PaymentAttemptStatus.REJECTED,
                response_payload=exc.response_payload,
                error_message=str(exc),
            )
            self._transition(
                db,
                payment,
                PaymentStatus.FAILED,
                reason="Daraja STK push request failed",
                failure_reason=str(exc),
                metadata_json=exc.response_payload,
            )
            db.commit()
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to initiate M-Pesa STK push") from exc

        checkout_request_id = response_payload.get("CheckoutRequestID")
        merchant_request_id = response_payload.get("MerchantRequestID")
        response_code = str(response_payload.get("ResponseCode", ""))
        if response_code != "0" or not checkout_request_id or not merchant_request_id:
            self.repository.update_attempt(
                attempt,
                status=PaymentAttemptStatus.REJECTED,
                response_payload=response_payload,
                checkout_request_id=checkout_request_id,
                merchant_request_id=merchant_request_id,
                error_message=str(response_payload.get("ResponseDescription", "STK push rejected")),
            )
            self._transition(
                db,
                payment,
                PaymentStatus.FAILED,
                reason="Daraja rejected STK push request",
                provider_result_code=response_code,
                provider_result_description=response_payload.get("ResponseDescription"),
                failure_reason=response_payload.get("ResponseDescription", "STK push rejected"),
                metadata_json=response_payload,
            )
            db.commit()
            return self._stk_response(payment, "STK push rejected by provider")

        self.repository.update_attempt(
            attempt,
            status=PaymentAttemptStatus.ACCEPTED,
            response_payload=response_payload,
            checkout_request_id=checkout_request_id,
            merchant_request_id=merchant_request_id,
        )
        next_reconciliation_at = datetime.now(UTC) + timedelta(minutes=self.settings.daraja_reconciliation_interval_minutes)
        self.repository.mark_stk_accepted(
            payment,
            checkout_request_id=checkout_request_id,
            merchant_request_id=merchant_request_id,
            next_reconciliation_at=next_reconciliation_at,
        )
        self.repository.add_status_history(
            db,
            payment=payment,
            from_status=PaymentStatus.PENDING,
            to_status=PaymentStatus.PROCESSING,
            reason="Daraja accepted STK push request",
            metadata_json=response_payload,
        )
        db.commit()
        db.refresh(payment)
        return self._stk_response(payment, response_payload.get("CustomerMessage", "STK push sent"))

    def fetch_payment(self, db: Session, current_user: User, payment_id: int) -> PaymentResponse:
        payment = self.repository.get_by_id(db, payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if payment.student_id != current_user.id and current_user.role not in {RoleEnum.admin, RoleEnum.vendor}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Payment is not available")
        return PaymentResponse.model_validate(payment)

    def fetch_my_payments(self, db: Session, current_user: User) -> list[PaymentResponse]:
        payments = self.repository.list_for_customer(db, current_user.id)
        return [PaymentResponse.model_validate(payment) for payment in payments]

    def update_payment_status(
        self,
        db: Session,
        payment_id: int,
        data: PaymentStatusUpdate,
        background_tasks: BackgroundTasks | None = None,
    ) -> PaymentResponse:
        payment = self.repository.get_by_id(db, payment_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        previous_status = payment.status
        self._transition(
            db,
            payment,
            data.status,
            reason="Manual payment status update",
            provider_reference=data.provider_reference,
            failure_reason=data.failure_reason,
        )
        db.commit()
        db.refresh(payment)
        if previous_status != PaymentStatus.SUCCESS and payment.status == PaymentStatus.SUCCESS:
            self._queue_transaction_receipt_email(db, payment, background_tasks)
        return PaymentResponse.model_validate(payment)

    def query_stk_status(
        self,
        db: Session,
        current_user: User,
        checkout_request_id: str,
        background_tasks: BackgroundTasks | None = None,
    ) -> STKQueryResponse:
        payment = self.repository.get_by_checkout_request_id(db, checkout_request_id)
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if payment.student_id != current_user.id and current_user.role not in {RoleEnum.admin, RoleEnum.vendor}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Payment is not available")
        previous_status = payment.status
        self._query_and_apply_result(db, payment)
        db.commit()
        db.refresh(payment)
        if previous_status != PaymentStatus.SUCCESS and payment.status == PaymentStatus.SUCCESS:
            self._queue_transaction_receipt_email(db, payment, background_tasks)
        return STKQueryResponse(
            payment_id=payment.id,
            status=payment.status,
            checkout_request_id=payment.checkout_request_id,
            provider_result_code=payment.provider_result_code,
            provider_result_description=payment.provider_result_description,
        )

    def handle_callback(
        self,
        db: Session,
        payload: dict[str, Any],
        background_tasks: BackgroundTasks | None = None,
    ) -> DarajaCallbackResponse:
        callback_data = self._extract_callback(payload)
        payload_hash = self._payload_hash(payload)
        existing_callback = self.repository.get_callback_by_hash(db, payload_hash)
        if existing_callback is not None:
            return DarajaCallbackResponse(result_description="Duplicate callback ignored")

        try:
            callback_log = self.repository.create_callback_log(
                db,
                checkout_request_id=callback_data["checkout_request_id"],
                merchant_request_id=callback_data["merchant_request_id"],
                result_code=callback_data["result_code"],
                payload_hash=payload_hash,
                raw_payload=payload,
            )
        except IntegrityError:
            db.rollback()
            return DarajaCallbackResponse(result_description="Duplicate callback ignored")

        payment = self.repository.get_by_checkout_request_id(db, callback_data["checkout_request_id"])
        if payment is None:
            self.repository.mark_callback_failed(callback_log, "Payment not found for CheckoutRequestID")
            db.commit()
            return DarajaCallbackResponse(result_description="Callback logged; payment not found")

        try:
            status_to_apply = self._status_from_result_code(callback_data["result_code"])
            previous_status = payment.status
            if payment.status in TERMINAL_STATUSES:
                self.repository.mark_callback_processed(callback_log)
                db.commit()
                return DarajaCallbackResponse(result_description="Callback logged; payment already terminal")
            self._transition(
                db,
                payment,
                status_to_apply,
                reason="Daraja callback received",
                provider_reference=callback_data["mpesa_receipt_number"],
                provider_result_code=str(callback_data["result_code"]),
                provider_result_description=callback_data["result_description"],
                failure_reason=None if status_to_apply == PaymentStatus.SUCCESS else callback_data["result_description"],
                metadata_json=payload,
            )
            if status_to_apply == PaymentStatus.SUCCESS:
                self.repository.create_transaction(
                    db,
                    payment=payment,
                    transaction_type=TransactionType.CALLBACK,
                    provider_transaction_id=callback_data["mpesa_receipt_number"],
                    amount=callback_data["amount"],
                    phone_number=callback_data["phone_number"],
                    raw_payload=payload,
                    occurred_at=callback_data["transaction_date"],
                )
            self.repository.mark_callback_processed(callback_log)
            db.commit()
            if previous_status != PaymentStatus.SUCCESS and payment.status == PaymentStatus.SUCCESS:
                self._queue_transaction_receipt_email(db, payment, background_tasks)
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Callback processing failed") from exc

        return DarajaCallbackResponse()

    def reconcile_due_payments(self, db: Session, *, limit: int = 50) -> int:
        payments = self.repository.list_due_for_reconciliation(db, now=datetime.now(UTC), limit=limit)
        processed_count = 0
        for payment in payments:
            self._query_and_apply_result(db, payment)
            processed_count += 1
        db.commit()
        return processed_count

    def _query_and_apply_result(self, db: Session, payment: Payment) -> None:
        if payment.checkout_request_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment has no CheckoutRequestID")
        if payment.status in TERMINAL_STATUSES:
            return

        try:
            payload = self.daraja_client.query_stk_push(checkout_request_id=payment.checkout_request_id)
        except DarajaAPIError as exc:
            next_reconciliation_at = self._next_reconciliation_at(payment)
            self.repository.mark_query_attempt(payment, queried_at=datetime.now(UTC), next_reconciliation_at=next_reconciliation_at)
            if payment.retry_count >= self.settings.daraja_max_query_retries:
                self._transition(
                    db,
                    payment,
                    PaymentStatus.TIMEOUT,
                    reason="Daraja query retries exhausted",
                    failure_reason=str(exc),
                    metadata_json=exc.response_payload,
                )
            return

        result_code = payload.get("ResultCode")
        if result_code is None:
            next_reconciliation_at = self._next_reconciliation_at(payment)
            self.repository.mark_query_attempt(payment, queried_at=datetime.now(UTC), next_reconciliation_at=next_reconciliation_at)
            return

        new_status = self._status_from_result_code(int(result_code))
        self.repository.mark_query_attempt(payment, queried_at=datetime.now(UTC), next_reconciliation_at=None)
        self._transition(
            db,
            payment,
            new_status,
            reason="Daraja STK query result",
            provider_result_code=str(result_code),
            provider_result_description=payload.get("ResultDesc"),
            failure_reason=None if new_status == PaymentStatus.SUCCESS else payload.get("ResultDesc"),
            metadata_json=payload,
        )

    def _get_payable_order(self, db: Session, current_user: User, order_id: int):
        order = self.repository.get_order(db, order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.student_id != current_user.id and current_user.role != RoleEnum.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Order is not available")
        if order.status == OrderStatus.CANCELLED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancelled orders cannot be paid")
        return order

    def _transition(
        self,
        db: Session,
        payment: Payment,
        target_status: PaymentStatus,
        *,
        reason: str,
        provider_reference: str | None = None,
        provider_result_code: str | None = None,
        provider_result_description: str | None = None,
        failure_reason: str | None = None,
        metadata_json: dict[str, Any] | None = None,
        changed_by_id: int | None = None,
    ) -> None:
        if payment.status == target_status:
            return
        if target_status not in ALLOWED_TRANSITIONS[payment.status]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Invalid payment transition from {payment.status.value} to {target_status.value}",
            )
        self.repository.update_status(
            db,
            payment,
            status=target_status,
            reason=reason,
            provider_reference=provider_reference,
            provider_result_code=provider_result_code,
            provider_result_description=provider_result_description,
            failure_reason=failure_reason,
            metadata_json=metadata_json,
            changed_by_id=changed_by_id,
        )

    def _next_reconciliation_at(self, payment: Payment) -> datetime | None:
        if payment.retry_count + 1 >= self.settings.daraja_max_query_retries:
            return None
        backoff_minutes = self.settings.daraja_reconciliation_interval_minutes * max(1, payment.retry_count + 1)
        return datetime.now(UTC) + timedelta(minutes=backoff_minutes)

    def _queue_transaction_receipt_email(
        self,
        db: Session,
        payment: Payment,
        background_tasks: BackgroundTasks | None,
    ) -> None:
        if self.notification_service is None:
            return

        try:
            order = self.repository.get_order(db, payment.order_id)
            order_number = order.order_code if order is not None else f"ORDER-{payment.order_id}"
            service_name = "Laundry service"
            if order is not None and getattr(order, "service_item", None) is not None:
                service_name = order.service_item.name

            self.notification_service.send_transaction_receipt_email(
                db,
                background_tasks,
                student_id=payment.student_id,
                order_number=order_number,
                services=[service_name],
                total=payment.amount,
                payment_status=payment.status.value,
                timestamp=payment.paid_at,
            )
        except Exception as exc:
            db.rollback()
            from app.core.logger import logger

            logger.error(f"Transaction receipt email queue failed | payment_id={payment.id} | error={exc}")

    @staticmethod
    def _status_from_result_code(result_code: int) -> PaymentStatus:
        code = str(result_code)
        if code in SUCCESS_RESULT_CODES:
            return PaymentStatus.SUCCESS
        if code in CANCELLED_RESULT_CODES:
            return PaymentStatus.CANCELLED
        if code in TIMEOUT_RESULT_CODES:
            return PaymentStatus.TIMEOUT
        return PaymentStatus.FAILED

    @staticmethod
    def _stk_response(payment: Payment, customer_message: str) -> STKPushResponse:
        return STKPushResponse(
            payment_id=payment.id,
            status=payment.status,
            checkout_request_id=payment.checkout_request_id,
            merchant_request_id=payment.merchant_request_id,
            customer_message=customer_message,
        )

    @staticmethod
    def _payload_hash(payload: dict[str, Any]) -> str:
        canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_payload.encode()).hexdigest()

    @staticmethod
    def _extract_callback(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            stk_callback = payload["Body"]["stkCallback"]
            metadata_items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid Daraja callback") from exc

        metadata = {item.get("Name"): item.get("Value") for item in metadata_items if item.get("Name")}
        transaction_date = metadata.get("TransactionDate")
        parsed_transaction_date = None
        if transaction_date:
            parsed_transaction_date = datetime.strptime(str(transaction_date), "%Y%m%d%H%M%S").replace(tzinfo=UTC)

        return {
            "merchant_request_id": stk_callback.get("MerchantRequestID"),
            "checkout_request_id": stk_callback.get("CheckoutRequestID"),
            "result_code": int(stk_callback.get("ResultCode")),
            "result_description": stk_callback.get("ResultDesc"),
            "amount": metadata.get("Amount"),
            "mpesa_receipt_number": metadata.get("MpesaReceiptNumber"),
            "phone_number": str(metadata.get("PhoneNumber")) if metadata.get("PhoneNumber") else None,
            "transaction_date": parsed_transaction_date,
        }
