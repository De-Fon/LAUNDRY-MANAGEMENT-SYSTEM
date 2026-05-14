from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.apps.notifications.providers import provide_notification_service
from app.apps.notifications.schemas import NotificationCreate, NotificationResponse
from app.apps.notifications.service import NotificationService
from app.apps.users.models import User
from app.core.database import get_db
from app.shared.auth import get_current_user, require_admin


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("", response_model=NotificationResponse, dependencies=[Depends(require_admin)])
def create_notification(
    data: NotificationCreate,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> NotificationResponse:
    return service.create_notification(db, data)


@router.get("/me", response_model=list[NotificationResponse])
def get_my_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> list[NotificationResponse]:
    return service.fetch_my_notifications(db, current_user)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> NotificationResponse:
    return service.mark_read(db, current_user, notification_id)
