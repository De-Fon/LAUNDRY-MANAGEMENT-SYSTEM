from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.apps.waitlist.providers import provide_waitlist_service
from app.apps.waitlist.schemas import WaitlistEntryCreate, WaitlistEntryResponse, WaitlistStatusUpdate
from app.apps.waitlist.service import WaitlistService
from app.core.database import get_db
from app.shared.auth import AuthenticatedUser, get_current_user


router = APIRouter(prefix="/waitlist", tags=["Waitlist"])


@router.post("", response_model=WaitlistEntryResponse, status_code=status.HTTP_201_CREATED)
def join_waitlist(
    data: WaitlistEntryCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[WaitlistService, Depends(provide_waitlist_service)],
) -> WaitlistEntryResponse:
    return service.join_waitlist(db, current_user, data)


@router.get("/me", response_model=list[WaitlistEntryResponse])
def get_my_waitlist_entries(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[WaitlistService, Depends(provide_waitlist_service)],
) -> list[WaitlistEntryResponse]:
    return service.fetch_my_entries(db, current_user)


@router.patch("/{entry_id}/status", response_model=WaitlistEntryResponse)
def update_waitlist_status(
    entry_id: int,
    data: WaitlistStatusUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[WaitlistService, Depends(provide_waitlist_service)],
) -> WaitlistEntryResponse:
    return service.update_status(db, current_user, entry_id, data)
