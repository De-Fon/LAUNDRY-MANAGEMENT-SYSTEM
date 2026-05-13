from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.apps.vendor_dashboard.providers import provide_vendor_service
from app.apps.vendor_dashboard.schemas import (
    BulkStatusUpdate,
    BulkStatusUpdateResponse,
    DashboardSummaryResponse,
    VendorCapacityResponse,
    VendorProfileCreate,
    VendorProfileResponse,
    VendorProfileUpdate,
    VendorStatusUpdate,
)
from app.apps.vendor_dashboard.service import VendorDashboardService
from app.core.database import get_db
from app.shared.auth import AuthenticatedUser, require_vendor


router = APIRouter(prefix="/vendor", tags=["Vendor Dashboard"])


@router.post("/profile", response_model=VendorProfileResponse)
def create_vendor_profile(
    data: VendorProfileCreate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[VendorDashboardService, Depends(provide_vendor_service)],
) -> VendorProfileResponse:
    return service.setup_vendor_profile(db, current_user.id, data)


@router.put("/profile", response_model=VendorProfileResponse)
def update_vendor_profile(
    data: VendorProfileUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[VendorDashboardService, Depends(provide_vendor_service)],
) -> VendorProfileResponse:
    return service.update_profile(db, current_user.id, data)


@router.patch("/status", response_model=VendorProfileResponse)
def toggle_vendor_status(
    data: VendorStatusUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[VendorDashboardService, Depends(provide_vendor_service)],
) -> VendorProfileResponse:
    return service.toggle_open_status(db, current_user.id, data.is_open)


@router.get("/dashboard", response_model=DashboardSummaryResponse)
def get_dashboard(
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[VendorDashboardService, Depends(provide_vendor_service)],
) -> DashboardSummaryResponse:
    return service.fetch_dashboard(db, current_user.id)


@router.patch("/orders/bulk-status", response_model=BulkStatusUpdateResponse)
def bulk_update_status(
    data: BulkStatusUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[VendorDashboardService, Depends(provide_vendor_service)],
) -> BulkStatusUpdateResponse:
    return service.bulk_update_status(db, current_user.id, data.order_ids, data.status)


@router.get("/capacity", response_model=VendorCapacityResponse)
def check_capacity(
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[VendorDashboardService, Depends(provide_vendor_service)],
    target_date: Annotated[date, Query(alias="date")],
) -> VendorCapacityResponse:
    return service.check_capacity(db, current_user.id, target_date)


@router.get("/{vendor_id}/available", response_model=bool)
def check_vendor_available(
    vendor_id: int,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[VendorDashboardService, Depends(provide_vendor_service)],
) -> bool:
    return service.is_vendor_available(db, vendor_id)
