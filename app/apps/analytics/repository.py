from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.apps.analytics.models import AnalyticsSnapshot
from app.apps.order_management.models import Order, OrderStatus


class AnalyticsRepository:
    def get_orders_in_period(self, db: Session, vendor_id: int, start: date, end: date) -> list[Order]:
        statement = (
            select(Order)
            .options(joinedload(Order.service_item), joinedload(Order.student))
            .where(
                Order.vendor_id == vendor_id,
                Order.created_at >= start,
                Order.created_at < end + timedelta(days=1),  # Include end date
            )
        )
        return list(db.scalars(statement).all())

    def get_revenue_in_period(self, db: Session, vendor_id: int, start: date, end: date) -> float:
        from app.apps.order_management.models import OrderStatus
        statement = select(func.sum(Order.total_price)).where(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.PICKED_UP,
            Order.created_at >= start,
            Order.created_at < end + timedelta(days=1),
        )
        result = db.scalar(statement)
        return result or 0.0

    def get_refunds_in_period(self, db: Session, vendor_id: int, start: date, end: date) -> float:
        from app.apps.ledger.models import LedgerAccount, LedgerTransaction, TransactionType

        statement = (
            select(func.coalesce(func.sum(LedgerTransaction.amount), 0.0))
            .join(LedgerAccount, LedgerTransaction.ledger_account_id == LedgerAccount.id)
            .where(
                LedgerAccount.vendor_id == vendor_id,
                LedgerTransaction.transaction_type == TransactionType.REFUND,
                LedgerTransaction.created_at >= start,
                LedgerTransaction.created_at < end + timedelta(days=1),
            )
        )
        result = db.scalar(statement)
        return float(result or 0.0)

    def get_outstanding_in_period(self, db: Session, vendor_id: int, start: date, end: date) -> float:
        from app.apps.ledger.models import LedgerAccount

        statement = select(func.coalesce(func.sum(LedgerAccount.total_outstanding), 0.0)).where(
            LedgerAccount.vendor_id == vendor_id,
        )
        result = db.scalar(statement)
        return float(result or 0.0)

    def get_order_count_by_status(self, db: Session, vendor_id: int, start: date, end: date) -> dict[str, int]:
        statement = select(Order.status, func.count(Order.id)).where(
            Order.vendor_id == vendor_id,
            Order.created_at >= start,
            Order.created_at < end + timedelta(days=1),
        ).group_by(Order.status)
        results = db.execute(statement).all()
        return {status.value: count for status, count in results}

    def get_top_items(self, db: Session, vendor_id: int, start: date, end: date, limit: int = 5) -> list[tuple[int, str, int, float]]:
        from app.apps.catalog.models import ServiceItem
        statement = (
            select(
                Order.service_item_id,
                ServiceItem.name,
                func.count(Order.id),
                func.sum(Order.total_price),
            )
            .join(ServiceItem, Order.service_item_id == ServiceItem.id)
            .where(
                Order.vendor_id == vendor_id,
                Order.created_at >= start,
                Order.created_at < end + timedelta(days=1),
            )
            .group_by(Order.service_item_id, ServiceItem.name)
            .order_by(func.count(Order.id).desc(), func.sum(Order.total_price).desc())
            .limit(limit)
        )
        return list(db.execute(statement).all())

    def get_hourly_breakdown(self, db: Session, vendor_id: int, start: date, end: date) -> list[tuple[int, int, float]]:
        statement = (
            select(
                func.extract('hour', Order.created_at),
                func.count(Order.id),
                func.sum(Order.total_price),
            )
            .where(
                Order.vendor_id == vendor_id,
                Order.created_at >= start,
                Order.created_at < end + timedelta(days=1),
            )
            .group_by(func.extract('hour', Order.created_at))
            .order_by(func.extract('hour', Order.created_at))
        )
        return list(db.execute(statement).all())

    def get_daily_revenue(self, db: Session, vendor_id: int, start: date, end: date) -> list[tuple[date, int, float, int]]:
        statement = (
            select(
                func.date(Order.created_at),
                func.count(Order.id),
                func.sum(Order.total_price),
                func.count().filter(Order.status == OrderStatus.PICKED_UP),
            )
            .where(
                Order.vendor_id == vendor_id,
                Order.created_at >= start,
                Order.created_at < end + timedelta(days=1),
            )
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        return list(db.execute(statement).all())

    def save_snapshot(self, db: Session, snapshot: AnalyticsSnapshot) -> AnalyticsSnapshot:
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    def get_snapshots_by_vendor(self, db: Session, vendor_id: int) -> list[AnalyticsSnapshot]:
        statement = select(AnalyticsSnapshot).where(AnalyticsSnapshot.vendor_id == vendor_id).order_by(AnalyticsSnapshot.created_at.desc())
        return list(db.scalars(statement).all())

    def get_snapshot_by_period(self, db: Session, vendor_id: int, report_type: str, period_start: date, period_end: date) -> AnalyticsSnapshot | None:
        statement = select(AnalyticsSnapshot).where(
            AnalyticsSnapshot.vendor_id == vendor_id,
            AnalyticsSnapshot.report_type == report_type,
            AnalyticsSnapshot.period_start == period_start,
            AnalyticsSnapshot.period_end == period_end,
        )
        return db.scalar(statement)