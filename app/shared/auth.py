from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.apps.auth.service import AuthService
from app.apps.users.models import RoleEnum, User
from app.core.database import get_db

AuthenticatedUser = User
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _provide_auth_service(
    db: Annotated[Session, Depends(get_db)],
) -> AuthService:
    from app.apps.auth.providers import provide_auth_repository
    from app.apps.users.providers import provide_user_repository

    return AuthService(provide_auth_repository(), provide_user_repository())


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthService, Depends(_provide_auth_service)],
) -> User:
    return service.get_current_user(db, token)


def require_vendor(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(_provide_auth_service)],
) -> User:
    return service.require_role(current_user, {RoleEnum.vendor, RoleEnum.admin})


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(_provide_auth_service)],
) -> User:
    return service.require_role(current_user, {RoleEnum.admin})


def require_student(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[AuthService, Depends(_provide_auth_service)],
) -> User:
    return service.require_role(current_user, {RoleEnum.student})
