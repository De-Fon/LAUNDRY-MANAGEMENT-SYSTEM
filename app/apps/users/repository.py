from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.apps.users.models import RoleEnum, User
from app.apps.users.schemas import UserUpdate


class UserRepository:
    def get_by_id(self, db: Session, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id, User.is_active.is_(True))
        return db.scalar(statement)

    def get_by_email(self, db: Session, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return db.scalar(statement)

    def get_by_phone(self, db: Session, phone: str) -> User | None:
        statement = select(User).where(User.phone == phone)
        return db.scalar(statement)

    def get_by_student_id(self, db: Session, student_id: str) -> User | None:
        statement = select(User).where(User.student_id == student_id)
        return db.scalar(statement)

    def find_by_identity(self, db: Session, email: str, phone: str, student_id: str | None = None) -> User | None:
        conditions = [User.email == email, User.phone == phone]
        if student_id is not None:
            conditions.append(User.student_id == student_id)
        statement = select(User).where(or_(*conditions))
        return db.scalar(statement)

    def list_users(self, db: Session, limit: int = 100, offset: int = 0) -> list[User]:
        statement = select(User).where(User.is_active.is_(True)).order_by(User.created_at.desc()).limit(limit).offset(offset)
        return list(db.scalars(statement).all())

    def create_user(
        self,
        db: Session,
        *,
        name: str,
        phone: str,
        email: str,
        password_hash: str,
        role: RoleEnum,
        student_id: str | None = None,
    ) -> User:
        user = User(
            name=name,
            phone=phone,
            email=email,
            password_hash=password_hash,
            role=role,
            student_id=student_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_user(self, db: Session, user: User, data: UserUpdate) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        db.commit()
        db.refresh(user)
        return user

    def mark_verified(self, db: Session, user: User) -> User:
        user.is_verified = True
        db.commit()
        db.refresh(user)
        return user

    def deactivate_user(self, db: Session, user: User) -> User:
        user.is_active = False
        db.commit()
        db.refresh(user)
        return user
