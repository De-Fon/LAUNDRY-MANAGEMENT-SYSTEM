from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    MPESA = "mpesa"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    REVERSED = "reversed"


class PaymentAttemptStatus(str, enum.Enum):
    STARTED = "started"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    QUERY_SUCCESS = "query_success"
    QUERY_FAILED = "query_failed"


class TransactionType(str, enum.Enum):
    STK_PUSH = "stk_push"
    STK_QUERY = "stk_query"
    CALLBACK = "callback"
    REVERSAL = "reversal"


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("provider_reference", name="uq_payments_provider_reference"),
        UniqueConstraint("idempotency_key", name="uq_payments_idempotency_key"),
        UniqueConstraint("checkout_request_id", name="uq_payments_checkout_request_id"),
        Index("ix_payments_student_status", "student_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, values_callable=enum_values), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, values_callable=enum_values),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    account_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checkout_request_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    merchant_request_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_result_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    provider_result_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_queried_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_reconciliation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    order: Mapped["Order"] = relationship(back_populates="payments")
    student: Mapped["User"] = relationship(back_populates="payments")
    attempts: Mapped[list["PaymentAttempt"]] = relationship(back_populates="payment", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="payment", cascade="all, delete-orphan")
    status_history: Mapped[list["PaymentStatusHistory"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
    )


class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (UniqueConstraint("checkout_request_id", name="uq_payment_attempts_checkout_request_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PaymentAttemptStatus] = mapped_column(
        Enum(PaymentAttemptStatus, values_callable=enum_values),
        default=PaymentAttemptStatus.STARTED,
        nullable=False,
    )
    checkout_request_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    merchant_request_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    payment: Mapped[Payment] = relationship(back_populates="attempts")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("provider_transaction_id", name="uq_transactions_provider_transaction_id"),
        Index("ix_transactions_payment_type", "payment_id", "transaction_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True, nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, values_callable=enum_values), nullable=False)
    provider_transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    payment: Mapped[Payment] = relationship(back_populates="transactions")


class CallbackLog(Base):
    __tablename__ = "callback_logs"
    __table_args__ = (
        UniqueConstraint("payload_hash", name="uq_callback_logs_payload_hash"),
        Index("ix_callback_logs_checkout_processed", "checkout_request_id", "processed"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    checkout_request_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    merchant_request_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    result_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PaymentStatusHistory(Base):
    __tablename__ = "payment_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True, nullable=False)
    from_status: Mapped[PaymentStatus | None] = mapped_column(
        Enum(PaymentStatus, values_callable=enum_values),
        nullable=True,
    )
    to_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, values_callable=enum_values), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    payment: Mapped[Payment] = relationship(back_populates="status_history")
