from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.apps.pricing.providers import provide_pricing_service
from app.shared.auth import AuthenticatedUser, get_current_user, require_vendor
from app.apps.pricing.schemas import PriceCalculationResponse, WashTypeCreate, WashTypeResponse
from app.apps.pricing.service import PricingService
from app.core.database import get_db


router = APIRouter(prefix="/pricing", tags=["Pricing"])


@router.get("/wash-types", response_model=list[WashTypeResponse])
def get_wash_types(
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PricingService, Depends(provide_pricing_service)],
) -> list[WashTypeResponse]:
    return service.fetch_wash_types(db)


@router.get("/calculate", response_model=PriceCalculationResponse)
def calculate_price(
    service: Annotated[PricingService, Depends(provide_pricing_service)],
    base_price: Annotated[float, Query(gt=0)],
    multiplier: Annotated[float, Query(gt=0)],
) -> PriceCalculationResponse:
    return service.calculate_price(base_price, multiplier)


@router.post("/rate-card/email", response_model=dict)
def email_rate_card(
    background_tasks: BackgroundTasks,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PricingService, Depends(provide_pricing_service)],
) -> dict:
    return service.email_rate_card(db, current_user, background_tasks)


@router.post("/wash-types", response_model=WashTypeResponse, dependencies=[Depends(require_vendor)], status_code=status.HTTP_201_CREATED)
def create_wash_type(
    data: WashTypeCreate,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PricingService, Depends(provide_pricing_service)],
) -> WashTypeResponse:
    return service.add_wash_type(db, data)
