import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.apps.order_management.models import Order
from app.core.database import Base


class TransactionType(str, enum.Enum):
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    ADJUSTMENT = "ADJUSTMENT"
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class TransactionStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class LedgerAccount(Base):
    __tablename__ = "ledger_accounts"
    __table_args__ = (UniqueConstraint("student_id", "vendor_id", name="uq_ledger_accounts_student_vendor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    total_billed: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_paid: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_outstanding: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_refunded: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    transactions: Mapped[list["LedgerTransaction"]] = relationship(
        back_populates="ledger_account",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["LedgerAuditLog"]] = relationship(
        back_populates="ledger_account",
        cascade="all, delete-orphan",
    )


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ledger_account_id: Mapped[int] = mapped_column(ForeignKey("ledger_accounts.id"), index=True, nullable=False)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True, nullable=True)
    transaction_type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, name="transaction_type"), nullable=False)
    transaction_status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status"),
        default=TransactionStatus.PENDING,
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    reference_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    ledger_account: Mapped[LedgerAccount] = relationship(back_populates="transactions")
    order: Mapped[Order | None] = relationship()
    audit_logs: Mapped[list["LedgerAuditLog"]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
    )


class LedgerAuditLog(Base):
    __tablename__ = "ledger_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ledger_account_id: Mapped[int] = mapped_column(ForeignKey("ledger_accounts.id"), index=True, nullable=False)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("ledger_transactions.id"), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    performed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    previous_balance: Mapped[float] = mapped_column(Float, nullable=False)
    new_balance: Mapped[float] = mapped_column(Float, nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ledger_account: Mapped[LedgerAccount] = relationship(back_populates="audit_logs")
    transaction: Mapped[LedgerTransaction] = relationship(back_populates="audit_logs")
