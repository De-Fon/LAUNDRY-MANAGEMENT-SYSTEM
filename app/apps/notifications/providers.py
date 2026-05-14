from typing import Annotated

from fastapi import Depends

from app.apps.notifications.repository import NotificationRepository
from app.apps.notifications.service import NotificationService


def provide_notification_repository() -> NotificationRepository:
    return NotificationRepository()


def provide_notification_service(
    repository: Annotated[NotificationRepository, Depends(provide_notification_repository)],
) -> NotificationService:
    return NotificationService(repository)

