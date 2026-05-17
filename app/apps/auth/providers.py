from typing import Annotated

from fastapi import Depends
from app.apps.auth.repository import AuthRepository
from app.apps.auth.service import AuthService
from app.apps.notifications.providers import provide_notification_service
from app.apps.notifications.service import NotificationService
from app.apps.users.repository import UserRepository
from app.apps.users.providers import provide_user_repository


def provide_auth_repository() -> AuthRepository:
    return AuthRepository()


def provide_auth_service(
    auth_repository: Annotated[AuthRepository, Depends(provide_auth_repository)],
    user_repository: Annotated[UserRepository, Depends(provide_user_repository)],
    notification_service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> AuthService:
    return AuthService(auth_repository, user_repository, notification_service)
