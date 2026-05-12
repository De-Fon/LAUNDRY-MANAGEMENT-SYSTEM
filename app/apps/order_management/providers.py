from typing import Annotated

from fastapi import Depends

from app.apps.catalog.providers import provide_catalog_repository
from app.apps.catalog.repository import CatalogRepository
from app.apps.order_management.repository import OrderRepository
from app.apps.order_management.service import OrderService
from app.apps.pricing.providers import provide_pricing_repository
from app.apps.pricing.repository import PricingRepository


def provide_order_repository() -> OrderRepository:
    return OrderRepository()


def provide_order_service(
    order_repository: Annotated[OrderRepository, Depends(provide_order_repository)],
    catalog_repository: Annotated[CatalogRepository, Depends(provide_catalog_repository)],
    pricing_repository: Annotated[PricingRepository, Depends(provide_pricing_repository)],
) -> OrderService:
    return OrderService(order_repository, catalog_repository, pricing_repository)
