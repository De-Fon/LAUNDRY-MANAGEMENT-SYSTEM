import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.apps.order_management.models import Order
from app.core.database import Base


class CreditStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    PARTIAL = "PARTIAL"
    PAID = "PAID"


class CreditTab(Base):
    __tablename__ = "credit_tabs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, index=True, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    outstanding_balance: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[CreditStatus] = mapped_column(
        Enum(CreditStatus, name="credit_status"),
        default=CreditStatus.UNPAID,
        nullable=False,
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    order: Mapped[Order] = relationship()
    payments: Mapped[list["CreditPayment"]] = relationship(
        back_populates="credit_tab",
        cascade="all, delete-orphan",
    )


class CreditPayment(Base):
    __tablename__ = "credit_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    credit_tab_id: Mapped[int] = mapped_column(ForeignKey("credit_tabs.id"), index=True, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    credit_tab: Mapped[CreditTab] = relationship(back_populates="payments")
