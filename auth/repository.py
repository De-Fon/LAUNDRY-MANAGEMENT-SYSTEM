from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.auth.models import OneTimePassword
from app.apps.users.models import User


class AuthRepository:
    def get_user_by_id(self, db: Session, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id, User.is_active.is_(True))
        return db.scalar(statement)

    def get_user_by_email(self, db: Session, email: str) -> User | None:
        statement = select(User).where(User.email == email, User.is_active.is_(True))
        return db.scalar(statement)

    def get_user_by_phone(self, db: Session, phone: str) -> User | None:
        statement = select(User).where(User.phone == phone, User.is_active.is_(True))
        return db.scalar(statement)

    def create_otp(
        self,
        db: Session,
        *,
        user_id: int,
        code_hash: str,
        purpose: str,
        expires_at: datetime,
    ) -> OneTimePassword:
        otp = OneTimePassword(user_id=user_id, code_hash=code_hash, purpose=purpose, expires_at=expires_at)
        db.add(otp)
        db.commit()
        db.refresh(otp)
        return otp

    def get_latest_open_otp(self, db: Session, user_id: int, purpose: str) -> OneTimePassword | None:
        statement = (
            select(OneTimePassword)
            .where(
                OneTimePassword.user_id == user_id,
                OneTimePassword.purpose == purpose,
                OneTimePassword.consumed_at.is_(None),
            )
            .order_by(OneTimePassword.created_at.desc())
            .limit(1)
        )
        return db.scalar(statement)

    def consume_otp(self, db: Session, otp: OneTimePassword) -> OneTimePassword:
        otp.consumed_at = datetime.now(UTC)
        db.commit()
        db.refresh(otp)
        return otp

    def mark_user_verified(self, db: Session, user: User) -> User:
        user.is_verified = True
        db.commit()
        db.refresh(user)
        return user
