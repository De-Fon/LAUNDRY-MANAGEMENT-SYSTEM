from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.apps.catalog.models import ServiceItem
from app.core.database import Base


class WashType(Base):
    __tablename__ = "wash_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price_multiplier: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    duration_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PriceOverride(Base):
    __tablename__ = "price_overrides"
    __table_args__ = (UniqueConstraint("vendor_id", "service_item_id", name="uq_price_overrides_vendor_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    service_item_id: Mapped[int] = mapped_column(ForeignKey("service_items.id"), index=True, nullable=False)
    custom_price: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    service_item: Mapped[ServiceItem] = relationship()
