from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter

from app.apps.auth.providers import provide_auth_service
from app.apps.auth.schemas import LoginRequest, OTPRequest, OTPVerifyRequest, RegisterRequest, TokenResponse
from app.apps.auth.service import AuthService
from app.apps.users.schemas import UserResponse
from app.shared.auth import AuthenticatedUser
from app.core.database import get_db
from app.shared.auth import get_current_user


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(
    request: Request,
    background_tasks: BackgroundTasks,
    data: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthService, Depends(provide_auth_service)],
) -> TokenResponse:
    return service.register(db, data, background_tasks)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    data: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthService, Depends(provide_auth_service)],
) -> TokenResponse:
    return service.login(db, data)


@router.post("/verify-phone", response_model=UserResponse)
def verify_phone(
    data: OTPVerifyRequest,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthService, Depends(provide_auth_service)],
) -> UserResponse:
    return service.verify_phone_otp(db, data)


@router.post("/password-reset", response_model=dict)
def request_password_reset(
    data: OTPRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthService, Depends(provide_auth_service)],
) -> dict:
    return service.request_password_reset_notification(db, data.email, background_tasks)


@router.get("/me", response_model=UserResponse)
def get_authenticated_user(current_user: Annotated[AuthenticatedUser, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(current_user)
