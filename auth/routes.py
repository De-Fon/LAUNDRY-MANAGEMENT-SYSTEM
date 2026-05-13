from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.apps.auth.providers import get_current_user, provide_auth_service
from app.apps.auth.schemas import LoginRequest, OTPVerifyRequest, RegisterRequest, TokenResponse
from app.apps.auth.service import AuthService
from app.apps.users.models import User
from app.apps.users.schemas import UserResponse
from app.core.database import get_db


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse)
def register(
    data: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[AuthService, Depends(provide_auth_service)],
) -> TokenResponse:
    return service.register(db, data)


@router.post("/login", response_model=TokenResponse)
def login(
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


@router.get("/me", response_model=UserResponse)
def get_authenticated_user(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(current_user)
