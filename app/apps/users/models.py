from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.apps.payments.models import Payment
    from app.apps.bookings.models import Booking
    from app.apps.notifications.models import Notification
    from app.apps.waitlist.models import WaitlistEntry

from app.core.database import Base


class RoleEnum(str, enum.Enum):
    student = "student"
    vendor = "vendor"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    student_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), default=RoleEnum.student, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    payments: Mapped[list["Payment"]] = relationship(back_populates="student")
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="customer",
        foreign_keys="Booking.customer_id",
    )
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(back_populates="customer")
