from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.pricing.models import WashType
from app.apps.pricing.schemas import WashTypeCreate


class PricingRepository:
    def get_all_wash_types(self, db: Session) -> list[WashType]:
        statement = select(WashType).where(WashType.is_active.is_(True)).order_by(WashType.name)
        return list(db.scalars(statement).all())

    def get_wash_type_by_name(self, db: Session, name: str) -> WashType | None:
        statement = select(WashType).where(WashType.name == name)
        return db.scalar(statement)

    def create_wash_type(self, db: Session, data: WashTypeCreate) -> WashType:
        wash_type = WashType(**data.model_dump())
        db.add(wash_type)
        db.commit()
        db.refresh(wash_type)
        return wash_type
