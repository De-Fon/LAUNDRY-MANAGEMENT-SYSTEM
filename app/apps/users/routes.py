from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.apps.users.providers import provide_user_service
from app.apps.users.schemas import UserCreate, UserResponse, UserUpdate
from app.apps.users.service import UserService
from app.core.database import get_db
from app.shared.auth import AuthenticatedUser, get_current_user, require_admin


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
def update_me(
    background_tasks: BackgroundTasks,
    data: UserUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[UserService, Depends(provide_user_service)],
) -> UserResponse:
    return service.update_user(db, current_user.id, data, background_tasks)


@router.post("", response_model=UserResponse, dependencies=[Depends(require_admin)], status_code=status.HTTP_201_CREATED)
def create_user(
    background_tasks: BackgroundTasks,
    data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[UserService, Depends(provide_user_service)],
) -> UserResponse:
    return service.register_user(db, data, background_tasks)


@router.get("", response_model=list[UserResponse], dependencies=[Depends(require_admin)])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[UserService, Depends(provide_user_service)],
    limit: Annotated[int, Query(gt=0, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[UserResponse]:
    return service.fetch_users(db, limit, offset)


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_admin)])
def get_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[UserService, Depends(provide_user_service)],
) -> UserResponse:
    return service.fetch_user(db, user_id)


@router.delete("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_admin)])
def deactivate_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[UserService, Depends(provide_user_service)],
) -> UserResponse:
    return service.deactivate_user(db, user_id)
