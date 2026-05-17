from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.apps.catalog.repository import CatalogRepository
from app.apps.notifications.service import NotificationService
from app.apps.pricing.repository import PricingRepository
from app.apps.pricing.schemas import PriceCalculationResponse, WashTypeCreate, WashTypeResponse
from app.apps.users.models import User
from app.core.pricing import calculate_final_price

class PricingService:
    def __init__(
        self,
        repository: PricingRepository,
        catalog_repository: CatalogRepository | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.repository = repository
        self.catalog_repository = catalog_repository
        self.notification_service = notification_service

    def fetch_wash_types(self, db: Session) -> list[WashTypeResponse]:
        return [WashTypeResponse.model_validate(wash_type) for wash_type in self.repository.get_all_wash_types(db)]

    def add_wash_type(self, db: Session, data: WashTypeCreate) -> WashTypeResponse:
        if self.repository.get_wash_type_by_name(db, data.name) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Wash type name already exists")

        wash_type = self.repository.create_wash_type(db, data)
        return WashTypeResponse.model_validate(wash_type)

    def calculate_price(self, base_price: float, multiplier: float) -> PriceCalculationResponse:
        if base_price <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Base price must be greater than 0")
        if multiplier <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Price multiplier must be greater than 0")

        return PriceCalculationResponse(
            base_price=base_price,
            multiplier=multiplier,
            final_price=calculate_final_price(base_price, multiplier),
        )

    def email_rate_card(
        self,
        db: Session,
        current_user: User,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict:
        if self.notification_service is None or self.catalog_repository is None:
            return {"message": "Rate card email skipped"}

        service_items = self.catalog_repository.get_all_items(db)
        services = [(item.name, item.base_price) for item in service_items]
        self.notification_service.send_rate_card_email(
            db,
            background_tasks,
            user_id=current_user.id,
            services=services,
        )
        return {"message": "Rate card email queued"}
