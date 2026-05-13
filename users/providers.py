from typing import Annotated

from fastapi import Depends

from app.apps.users.repository import UserRepository
from app.apps.users.service import UserService


def provide_user_repository() -> UserRepository:
    return UserRepository()


def provide_user_service(
    repository: Annotated[UserRepository, Depends(provide_user_repository)],
) -> UserService:
    return UserService(repository)
