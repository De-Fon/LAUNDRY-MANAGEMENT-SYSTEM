from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.pricing.repository import PricingRepository
from app.apps.pricing.schemas import PriceCalculationResponse, WashTypeCreate, WashTypeResponse


def calculate_final_price(base_price: float, multiplier: float) -> float:
    return round(base_price * multiplier, 2)


class PricingService:
    def __init__(self, repository: PricingRepository) -> None:
        self.repository = repository

    def fetch_wash_types(self, db: Session) -> list[WashTypeResponse]:
        return [WashTypeResponse.model_validate(wash_type) for wash_type in self.repository.get_all_wash_types(db)]

    def add_wash_type(self, db: Session, data: WashTypeCreate) -> WashTypeResponse:
        if self.repository.get_wash_type_by_name(db, data.name) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Wash type name already exists")

        wash_type = self.repository.create_wash_type(db, data)
        return WashTypeResponse.model_validate(wash_type)

    def calculate_price(self, base_price: float, multiplier: float) -> PriceCalculationResponse:
        self._validate_positive(base_price, "Base price")
        self._validate_positive(multiplier, "Price multiplier")
        return PriceCalculationResponse(
            base_price=base_price,
            multiplier=multiplier,
            final_price=calculate_final_price(base_price, multiplier),
        )

    def _validate_positive(self, value: float, field_name: str) -> None:
        if value <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be greater than 0",
            )
