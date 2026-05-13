from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.apps.auth.repository import AuthRepository
from app.apps.auth.service import AuthService
from app.apps.users.models import RoleEnum, User
from app.apps.users.repository import UserRepository
from app.apps.users.providers import provide_user_repository
from app.core.database import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def provide_auth_repository() -> AuthRepository:
    return AuthRepository()


def provide_auth_service(
    auth_repository: Annotated[AuthRepository, Depends(provide_auth_repository)],
    user_repository: Annotated[UserRepository, Depends(provide_user_repository)],
) -> AuthService:
    return AuthService(auth_repository, user_repository)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthService, Depends(provide_auth_service)],
) -> User:
    return service.get_current_user(db, token)


def require_vendor(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(provide_auth_service)],
) -> User:
    return service.require_role(current_user, {RoleEnum.vendor, RoleEnum.admin})


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(provide_auth_service)],
) -> User:
    return service.require_role(current_user, {RoleEnum.admin})
