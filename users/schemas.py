from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.apps.users.models import RoleEnum


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    phone: str = Field(..., min_length=7, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    student_id: str | None = Field(default=None, max_length=100)
    role: RoleEnum = RoleEnum.student


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, min_length=7, max_length=30)
    email: EmailStr | None = None
    student_id: str | None = Field(default=None, max_length=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    email: EmailStr
    student_id: str | None
    role: RoleEnum
    is_verified: bool
    is_active: bool
    created_at: datetime
