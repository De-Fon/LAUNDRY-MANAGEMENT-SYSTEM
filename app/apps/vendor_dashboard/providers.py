from typing import Annotated

from fastapi import Depends

from app.apps.order_management.providers import provide_order_repository
from app.apps.order_management.repository import OrderRepository
from app.apps.vendor_dashboard.repository import VendorDashboardRepository
from app.apps.vendor_dashboard.service import VendorDashboardService


def provide_vendor_repository() -> VendorDashboardRepository:
    return VendorDashboardRepository()


def provide_vendor_service(
    repository: Annotated[VendorDashboardRepository, Depends(provide_vendor_repository)],
    order_repository: Annotated[OrderRepository, Depends(provide_order_repository)],
) -> VendorDashboardService:
    return VendorDashboardService(repository, order_repository)
