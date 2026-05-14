from typing import Annotated

from fastapi import Depends
from app.apps.auth.repository import AuthRepository
from app.apps.auth.service import AuthService
from app.apps.users.repository import UserRepository
from app.apps.users.providers import provide_user_repository


def provide_auth_repository() -> AuthRepository:
    return AuthRepository()


def provide_auth_service(
    auth_repository: Annotated[AuthRepository, Depends(provide_auth_repository)],
    user_repository: Annotated[UserRepository, Depends(provide_user_repository)],
) -> AuthService:
    return AuthService(auth_repository, user_repository)
