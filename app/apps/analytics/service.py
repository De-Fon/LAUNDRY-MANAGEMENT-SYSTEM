from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.analytics.models import AnalyticsSnapshot, ReportType
from app.apps.analytics.repository import AnalyticsRepository
from app.apps.analytics.schemas import (
    AnalyticsRequest,
    DailyRevenueResponse,
    FullAnalyticsReportResponse,
    HourlyBreakdownResponse,
    StatusBreakdownResponse,
    TopItemResponse,
)
from app.apps.order_management.models import OrderStatus


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    def generate_report(self, db: Session, vendor_id: int, data: AnalyticsRequest) -> FullAnalyticsReportResponse:
        period_start, period_end = self._resolve_period(data.report_type, data.period_start, data.period_end)

        orders = self.repository.get_orders_in_period(db, vendor_id, period_start, period_end)
        total_orders = len(orders)
        total_revenue = self.repository.get_revenue_in_period(db, vendor_id, period_start, period_end)
        total_refunds = self.repository.get_refunds_in_period(db, vendor_id, period_start, period_end)
        total_outstanding = self.repository.get_outstanding_in_period(db, vendor_id, period_start, period_end)
        order_count_by_status = self.repository.get_order_count_by_status(db, vendor_id, period_start, period_end)
        top_items_raw = self.repository.get_top_items(db, vendor_id, period_start, period_end, limit=5)
        hourly_breakdown_raw = self.repository.get_hourly_breakdown(db, vendor_id, period_start, period_end)
        daily_revenue_raw = self.repository.get_daily_revenue(db, vendor_id, period_start, period_end)

        completed_orders = order_count_by_status.get(OrderStatus.PICKED_UP.value, 0)
        completion_rate = round((completed_orders / total_orders) * 100, 2) if total_orders > 0 else 0.0
        peak_hour = max(hourly_breakdown_raw, key=lambda x: x[1])[0] if hourly_breakdown_raw else None

        status_breakdown = [
            StatusBreakdownResponse(
                status=status,
                count=count,
                percentage=round((count / total_orders) * 100, 2) if total_orders > 0 else 0.0,
            )
            for status, count in order_count_by_status.items()
        ]

        top_items = [
            TopItemResponse(
                service_item_id=item_id,
                item_name=name,
                order_count=count,
                total_revenue=round(revenue, 2),
            )
            for item_id, name, count, revenue in top_items_raw
        ]

        hourly_breakdown = [
            HourlyBreakdownResponse(
                hour=int(hour),
                order_count=count,
                revenue=round(revenue, 2),
            )
            for hour, count, revenue in hourly_breakdown_raw
        ]

        daily_revenue = [
            DailyRevenueResponse(
                date=d,
                total_orders=total,
                total_revenue=round(rev, 2),
                completed_orders=comp,
            )
            for d, total, rev, comp in daily_revenue_raw
        ]

        report = FullAnalyticsReportResponse(
            vendor_id=vendor_id,
            report_type=data.report_type,
            period_start=period_start,
            period_end=period_end,
            total_orders=total_orders,
            total_revenue=round(total_revenue, 2),
            total_refunds=round(total_refunds, 2),
            total_outstanding=round(total_outstanding, 2),
            completed_orders=completed_orders,
            completion_rate=completion_rate,
            peak_hour=peak_hour,
            top_items=top_items,
            hourly_breakdown=hourly_breakdown,
            status_breakdown=status_breakdown,
            daily_revenue=daily_revenue,
        )

        snapshot = AnalyticsSnapshot(
            vendor_id=vendor_id,
            report_type=data.report_type,
            period_start=period_start,
            period_end=period_end,
            total_orders=total_orders,
            total_revenue=round(total_revenue, 2),
            total_refunds=round(total_refunds, 2),
            total_outstanding=round(total_outstanding, 2),
            completed_orders=completed_orders,
            cancelled_orders=order_count_by_status.get(OrderStatus.CANCELLED.value, 0),
            top_item_id=top_items[0].service_item_id if top_items else None,
            top_item_count=top_items[0].order_count if top_items else 0,
            peak_hour=peak_hour,
        )
        self.repository.save_snapshot(db, snapshot)
        return report

    def fetch_daily_report(self, db: Session, vendor_id: int) -> FullAnalyticsReportResponse:
        return self.generate_report(db, vendor_id, AnalyticsRequest(report_type=ReportType.DAILY))

    def fetch_weekly_report(self, db: Session, vendor_id: int) -> FullAnalyticsReportResponse:
        return self.generate_report(db, vendor_id, AnalyticsRequest(report_type=ReportType.WEEKLY))

    def fetch_monthly_report(self, db: Session, vendor_id: int) -> FullAnalyticsReportResponse:
        return self.generate_report(db, vendor_id, AnalyticsRequest(report_type=ReportType.MONTHLY))

    def fetch_custom_report(self, db: Session, vendor_id: int, period_start: date, period_end: date) -> FullAnalyticsReportResponse:
        if period_start > period_end:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_start must be before or equal to period_end")
        if (period_end - period_start).days > 365:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period range cannot exceed 365 days")
        return self.generate_report(db, vendor_id, AnalyticsRequest(report_type=ReportType.CUSTOM, period_start=period_start, period_end=period_end))

    def fetch_top_items(self, db: Session, vendor_id: int, period_start: date, period_end: date, limit: int = 5) -> list[TopItemResponse]:
        top_items_raw = self.repository.get_top_items(db, vendor_id, period_start, period_end, limit)
        return [
            TopItemResponse(
                service_item_id=item_id,
                item_name=name,
                order_count=count,
                total_revenue=round(revenue, 2),
            )
            for item_id, name, count, revenue in top_items_raw
        ]

    def fetch_snapshots(self, db: Session, vendor_id: int):
        snapshots = self.repository.get_snapshots_by_vendor(db, vendor_id)
        return snapshots

    def _resolve_period(self, report_type: ReportType, period_start: date | None, period_end: date | None) -> tuple[date, date]:
        today = date.today()
        if report_type == ReportType.DAILY:
            return today, today
        elif report_type == ReportType.WEEKLY:
            return today - timedelta(days=7), today
        elif report_type == ReportType.MONTHLY:
            return today - timedelta(days=30), today
        elif report_type == ReportType.CUSTOM:
            if period_start is None or period_end is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="period_start and period_end required for CUSTOM")
            return period_start, period_end
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report type")
