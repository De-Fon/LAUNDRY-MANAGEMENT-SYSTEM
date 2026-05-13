from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.apps.analytics.models import ReportType


class AnalyticsRequest(BaseModel):
    report_type: ReportType
    period_start: date | None = None
    period_end: date | None = None


class TopItemResponse(BaseModel):
    service_item_id: int
    item_name: str
    order_count: int
    total_revenue: float


class HourlyBreakdownResponse(BaseModel):
    hour: int
    order_count: int
    revenue: float


class StatusBreakdownResponse(BaseModel):
    status: str
    count: int
    percentage: float


class DailyRevenueResponse(BaseModel):
    date: date
    total_orders: int
    total_revenue: float
    completed_orders: int


class AnalyticsSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor_id: int
    report_type: ReportType
    period_start: date
    period_end: date
    total_orders: int
    total_revenue: float
    total_refunds: float
    total_outstanding: float
    completed_orders: int
    cancelled_orders: int
    top_item_id: int | None
    top_item_count: int
    peak_hour: int | None
    created_at: date


class FullAnalyticsReportResponse(BaseModel):
    vendor_id: int
    report_type: ReportType
    period_start: date
    period_end: date
    total_orders: int
    total_revenue: float
    total_refunds: float
    total_outstanding: float
    completed_orders: int
    completion_rate: float
    peak_hour: int | None
    top_items: list[TopItemResponse]
    hourly_breakdown: list[HourlyBreakdownResponse]
    status_breakdown: list[StatusBreakdownResponse]
    daily_revenue: list[DailyRevenueResponse]