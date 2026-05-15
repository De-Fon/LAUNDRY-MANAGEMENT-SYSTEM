from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.apps.auth.repository import AuthRepository
from app.apps.auth.schemas import LoginRequest, OTPVerifyRequest, RegisterRequest, TokenResponse
from app.apps.users.models import RoleEnum, User
from app.apps.users.repository import UserRepository
from app.apps.users.schemas import UserResponse
from app.core.security import ALGORITHM, create_access_token, hash_password, verify_password
from app.core.settings import get_settings


OTP_PURPOSE_PHONE_VERIFICATION = "phone_verification"
OTP_TTL_MINUTES = 10


class AuthService:
    def __init__(self, auth_repository: AuthRepository, user_repository: UserRepository) -> None:
        self.auth_repository = auth_repository
        self.user_repository = user_repository

    def register(self, db: Session, data: RegisterRequest) -> TokenResponse:
        existing_user = self.user_repository.find_by_identity(db, str(data.email), data.phone, data.student_id)
        if existing_user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User identity already exists")

        user = self.user_repository.create_user(
            db,
            name=data.name,
            phone=data.phone,
            email=str(data.email),
            password_hash=hash_password(data.password),
            role=data.role,
            student_id=data.student_id,
        )
        token = create_access_token(str(user.id), {"role": user.role.value})
        return TokenResponse(access_token=token, user=UserResponse.model_validate(user))

    def login(self, db: Session, data: LoginRequest) -> TokenResponse:
        user = self.auth_repository.get_user_by_email(db, str(data.email))
        if user is None or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        token = create_access_token(str(user.id), {"role": user.role.value})
        return TokenResponse(access_token=token, user=UserResponse.model_validate(user))

    def get_current_user(self, db: Session, token: str) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
            subject = payload.get("sub")
        except JWTError as exc:
            raise credentials_exception from exc

        if subject is None:
            raise credentials_exception

        user = self.auth_repository.get_user_by_id(db, int(subject))
        if user is None:
            raise credentials_exception
        return user

    def require_role(self, user: User, allowed_roles: set[RoleEnum]) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    def create_phone_verification_otp(self, db: Session, email: str, code: str) -> None:
        user = self.auth_repository.get_user_by_email(db, email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        self.auth_repository.create_otp(
            db,
            user_id=user.id,
            code_hash=hash_password(code),
            purpose=OTP_PURPOSE_PHONE_VERIFICATION,
            expires_at=datetime.now(UTC) + timedelta(minutes=OTP_TTL_MINUTES),
        )

    def verify_phone_otp(self, db: Session, data: OTPVerifyRequest) -> UserResponse:
        user = self.auth_repository.get_user_by_phone(db, data.phone)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        otp = self.auth_repository.get_latest_open_otp(db, user.id, OTP_PURPOSE_PHONE_VERIFICATION)
        if otp is None or otp.expires_at <= datetime.now(UTC) or not verify_password(data.otp, otp.code_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")

        self.auth_repository.consume_otp(db, otp)
        verified_user = self.auth_repository.mark_user_verified(db, user)
        return UserResponse.model_validate(verified_user)


