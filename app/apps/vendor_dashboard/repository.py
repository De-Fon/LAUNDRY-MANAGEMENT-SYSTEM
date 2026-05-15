from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.apps.order_management.models import Order, OrderStatus
from app.apps.vendor_dashboard.models import VendorCapacity, VendorProfile
from app.apps.vendor_dashboard.schemas import VendorProfileUpdate


class VendorDashboardRepository:
    def create_vendor_profile(self, db: Session, profile: VendorProfile) -> VendorProfile:
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    def get_vendor_profile(self, db: Session, vendor_id: int) -> VendorProfile | None:
        statement = select(VendorProfile).where(VendorProfile.vendor_id == vendor_id)
        return db.scalar(statement)

    def update_vendor_profile(self, db: Session, vendor_id: int, data: VendorProfileUpdate) -> VendorProfile | None:
        profile = self.get_vendor_profile(db, vendor_id)
        if profile is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(profile, field, value)

        db.commit()
        db.refresh(profile)
        return profile

    def toggle_vendor_open(self, db: Session, vendor_id: int, is_open: bool) -> VendorProfile | None:
        profile = self.get_vendor_profile(db, vendor_id)
        if profile is None:
            return None

        profile.is_open = is_open
        db.commit()
        db.refresh(profile)
        return profile

    def get_vendor_capacity(self, db: Session, vendor_id: int, target_date: date) -> VendorCapacity | None:
        statement = select(VendorCapacity).where(
            VendorCapacity.vendor_id == vendor_id,
            VendorCapacity.date == target_date,
        )
        return db.scalar(statement)

    def create_vendor_capacity(self, db: Session, capacity: VendorCapacity) -> VendorCapacity:
        db.add(capacity)
        db.commit()
        db.refresh(capacity)
        return capacity

    def increment_booked_slots(self, db: Session, vendor_id: int, target_date: date) -> VendorCapacity | None:
        capacity = self.get_vendor_capacity(db, vendor_id, target_date)
        if capacity is None:
            return None

        capacity.booked_slots += 1
        capacity.available_slots -= 1
        db.commit()
        db.refresh(capacity)
        return capacity

    def decrement_booked_slots(self, db: Session, vendor_id: int, target_date: date) -> VendorCapacity | None:
        capacity = self.get_vendor_capacity(db, vendor_id, target_date)
        if capacity is None:
            return None

        capacity.booked_slots -= 1
        capacity.available_slots += 1
        db.commit()
        db.refresh(capacity)
        return capacity

    def get_orders_today(self, db: Session, vendor_id: int, target_date: date) -> list[Order]:
        start, end = self._day_bounds(target_date)
        statement = (
            select(Order)
            .options(
                joinedload(Order.service_item),
                joinedload(Order.status_history),
                joinedload(Order.payments),
            )
            .where(Order.vendor_id == vendor_id, Order.created_at >= start, Order.created_at < end)
            .order_by(Order.created_at.desc())
        )
        return list(db.scalars(statement).unique().all())

    def get_orders_by_status(self, db: Session, vendor_id: int, status: OrderStatus) -> list[Order]:
        statement = (
            select(Order)
            .options(
                joinedload(Order.service_item),
                joinedload(Order.status_history),
                joinedload(Order.payments),
            )
            .where(Order.vendor_id == vendor_id, Order.status == status)
            .order_by(Order.created_at.desc())
        )
        return list(db.scalars(statement).unique().all())

    def count_orders_by_status(self, db: Session, vendor_id: int, target_date: date) -> dict[OrderStatus, int]:
        start, end = self._day_bounds(target_date)
        statement = (
            select(Order.status, func.count(Order.id))
            .where(Order.vendor_id == vendor_id, Order.created_at >= start, Order.created_at < end)
            .group_by(Order.status)
        )
        return {status: count for status, count in db.execute(statement).all()}

    def get_revenue_today(self, db: Session, vendor_id: int, target_date: date) -> float:
        start, end = self._day_bounds(target_date)
        statement = select(func.coalesce(func.sum(Order.total_price), 0.0)).where(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.PICKED_UP,
            Order.created_at >= start,
            Order.created_at < end,
        )
        return float(db.scalar(statement) or 0.0)

    def _day_bounds(self, target_date: date) -> tuple[datetime, datetime]:
        start = datetime.combine(target_date, time.min, tzinfo=UTC)
        return start, start + timedelta(days=1)
