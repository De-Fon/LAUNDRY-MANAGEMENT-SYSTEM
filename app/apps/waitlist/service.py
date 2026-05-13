from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.users.models import RoleEnum, User
from app.apps.waitlist.models import WaitlistStatus
from app.apps.waitlist.repository import WaitlistRepository
from app.apps.waitlist.schemas import WaitlistEntryCreate, WaitlistEntryResponse, WaitlistStatusUpdate


class WaitlistService:
    def __init__(self, repository: WaitlistRepository) -> None:
        self.repository = repository

    def join_waitlist(self, db: Session, current_user: User, data: WaitlistEntryCreate) -> WaitlistEntryResponse:
        if self.repository.get_service_item(db, data.service_item_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")

        existing_entry = self.repository.get_active_entry(db, current_user.id, data.service_item_id)
        if existing_entry is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already on waitlist")

        entry = self.repository.create_entry(
            db,
            customer_id=current_user.id,
            service_item_id=data.service_item_id,
            note=data.note,
        )
        return WaitlistEntryResponse.model_validate(entry)

    def fetch_my_entries(self, db: Session, current_user: User) -> list[WaitlistEntryResponse]:
        entries = self.repository.list_for_customer(db, current_user.id)
        return [WaitlistEntryResponse.model_validate(entry) for entry in entries]

    def update_status(
        self,
        db: Session,
        current_user: User,
        entry_id: int,
        data: WaitlistStatusUpdate,
    ) -> WaitlistEntryResponse:
        entry = self.repository.get_by_id(db, entry_id)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found")

        can_update = current_user.role in {RoleEnum.vendor, RoleEnum.admin} or entry.customer_id == current_user.id
        if not can_update:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Waitlist entry is not available")

        if current_user.role == RoleEnum.student and data.status not in {WaitlistStatus.cancelled, WaitlistStatus.converted}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students can only cancel or convert entries")

        updated_entry = self.repository.update_status(db, entry, data.status)
        return WaitlistEntryResponse.model_validate(updated_entry)
