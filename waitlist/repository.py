from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.catalog.models import ServiceItem
from app.apps.waitlist.models import WaitlistEntry, WaitlistStatus


class WaitlistRepository:
    def get_service_item(self, db: Session, service_item_id: int) -> ServiceItem | None:
        statement = select(ServiceItem).where(ServiceItem.id == service_item_id, ServiceItem.is_active.is_(True))
        return db.scalar(statement)

    def get_by_id(self, db: Session, entry_id: int) -> WaitlistEntry | None:
        statement = select(WaitlistEntry).where(WaitlistEntry.id == entry_id)
        return db.scalar(statement)

    def get_active_entry(self, db: Session, customer_id: int, service_item_id: int) -> WaitlistEntry | None:
        statement = select(WaitlistEntry).where(
            WaitlistEntry.customer_id == customer_id,
            WaitlistEntry.service_item_id == service_item_id,
            WaitlistEntry.status.in_([WaitlistStatus.waiting, WaitlistStatus.notified]),
        )
        return db.scalar(statement)

    def list_for_customer(self, db: Session, customer_id: int) -> list[WaitlistEntry]:
        statement = (
            select(WaitlistEntry)
            .where(WaitlistEntry.customer_id == customer_id)
            .order_by(WaitlistEntry.created_at.desc())
        )
        return list(db.scalars(statement).all())

    def create_entry(
        self,
        db: Session,
        *,
        customer_id: int,
        service_item_id: int,
        note: str | None,
    ) -> WaitlistEntry:
        entry = WaitlistEntry(customer_id=customer_id, service_item_id=service_item_id, note=note)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def update_status(self, db: Session, entry: WaitlistEntry, status: WaitlistStatus) -> WaitlistEntry:
        entry.status = status
        if status == WaitlistStatus.notified:
            entry.notified_at = datetime.now(UTC)
        if status == WaitlistStatus.converted:
            entry.converted_at = datetime.now(UTC)
        db.commit()
        db.refresh(entry)
        return entry
