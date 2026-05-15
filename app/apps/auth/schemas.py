from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.apps.users.models import RoleEnum
from app.apps.users.schemas import UserCreate, UserResponse


class RegisterRequest(UserCreate):
    pass


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class TokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    sub: str
    role: RoleEnum


class OTPVerifyRequest(BaseModel):
    phone: str = Field(..., min_length=7, max_length=30)
    otp: str = Field(..., min_length=4, max_length=10)


class OTPRequest(BaseModel):
    email: EmailStr
