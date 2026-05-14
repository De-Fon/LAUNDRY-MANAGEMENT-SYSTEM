import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.apps.catalog.models import ServiceItem
from app.core.database import Base


class OrderStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    WASHING = "WASHING"
    DRYING = "DRYING"
    READY = "READY"
    WAITING_TO_PICK = "WAITING_TO_PICK"
    PICKED_UP = "PICKED_UP"
    CANCELLED = "CANCELLED"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    service_item_id: Mapped[int] = mapped_column(ForeignKey("service_items.id"), index=True, nullable=False)
    wash_type: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    special_instructions: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        default=OrderStatus.QUEUED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    service_item: Mapped[ServiceItem] = relationship()
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")
    status_history: Mapped[list["OrderStatusLog"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    previous_status: Mapped[OrderStatus | None] = mapped_column(Enum(OrderStatus, name="order_status"), nullable=True)
    new_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status"), nullable=False)
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    note: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    order: Mapped[Order] = relationship(back_populates="status_history")
