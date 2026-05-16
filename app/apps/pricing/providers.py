from typing import Annotated

from fastapi import Depends

from app.apps.pricing.repository import PricingRepository
from app.apps.pricing.service import PricingService


def provide_pricing_repository() -> PricingRepository:
    return PricingRepository()


def provide_pricing_service(
    repository: Annotated[PricingRepository, Depends(provide_pricing_repository)],
) -> PricingService:
    return PricingService(repository)
