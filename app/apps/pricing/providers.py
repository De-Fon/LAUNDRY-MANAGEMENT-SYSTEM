from typing import Annotated

from fastapi import Depends

from app.apps.catalog.providers import provide_catalog_repository
from app.apps.catalog.repository import CatalogRepository
from app.apps.notifications.providers import provide_notification_service
from app.apps.notifications.service import NotificationService
from app.apps.pricing.repository import PricingRepository
from app.apps.pricing.service import PricingService


def provide_pricing_repository() -> PricingRepository:
    return PricingRepository()


def provide_pricing_service(
    repository: Annotated[PricingRepository, Depends(provide_pricing_repository)],
    catalog_repository: Annotated[CatalogRepository, Depends(provide_catalog_repository)],
    notification_service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> PricingService:
    return PricingService(repository, catalog_repository, notification_service)
