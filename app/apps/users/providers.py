from typing import Annotated

from fastapi import Depends

from app.apps.notifications.providers import provide_notification_service
from app.apps.notifications.service import NotificationService
from app.apps.users.repository import UserRepository
from app.apps.users.service import UserService


def provide_user_repository() -> UserRepository:
    return UserRepository()


def provide_user_service(
    repository: Annotated[UserRepository, Depends(provide_user_repository)],
    notification_service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> UserService:
    return UserService(repository, notification_service)
