from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.apps.analytics.providers import provide_analytics_service
from app.apps.analytics.schemas import (
    AnalyticsSnapshotResponse,
    FullAnalyticsReportResponse,
    TopItemResponse,
)
from app.apps.analytics.service import AnalyticsService
from app.core.database import get_db
from app.shared.auth import AuthenticatedUser, require_vendor


router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/daily", response_model=FullAnalyticsReportResponse)
def get_daily_analytics(
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnalyticsService, Depends(provide_analytics_service)],
) -> FullAnalyticsReportResponse:
    return service.fetch_daily_report(db, current_user.id)


@router.get("/weekly", response_model=FullAnalyticsReportResponse)
def get_weekly_analytics(
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnalyticsService, Depends(provide_analytics_service)],
) -> FullAnalyticsReportResponse:
    return service.fetch_weekly_report(db, current_user.id)


@router.get("/monthly", response_model=FullAnalyticsReportResponse)
def get_monthly_analytics(
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnalyticsService, Depends(provide_analytics_service)],
) -> FullAnalyticsReportResponse:
    return service.fetch_monthly_report(db, current_user.id)


@router.post("/custom", response_model=FullAnalyticsReportResponse)
def get_custom_analytics(
    period_start: date,
    period_end: date,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnalyticsService, Depends(provide_analytics_service)],
) -> FullAnalyticsReportResponse:
    return service.fetch_custom_report(db, current_user.id, period_start, period_end)


@router.get("/top-items", response_model=list[TopItemResponse])
def get_top_items(
    period_start: date,
    period_end: date,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnalyticsService, Depends(provide_analytics_service)],
    limit: int = Query(default=5, ge=1, le=20),
) -> list[TopItemResponse]:
    return service.fetch_top_items(db, current_user.id, period_start, period_end, limit)


@router.get("/snapshots", response_model=list[AnalyticsSnapshotResponse])
def get_analytics_snapshots(
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AnalyticsService, Depends(provide_analytics_service)],
) -> list[AnalyticsSnapshotResponse]:
    return service.fetch_snapshots(db, current_user.id)
