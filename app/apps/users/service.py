from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.users.repository import UserRepository
from app.apps.users.schemas import UserCreate, UserResponse, UserUpdate
from app.core.security import hash_password

class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    def fetch_users(self, db: Session, limit: int = 100, offset: int = 0) -> list[UserResponse]:
        users = self.repository.list_users(db, limit, offset)
        return [UserResponse.model_validate(user) for user in users]

    def fetch_user(self, db: Session, user_id: int) -> UserResponse:
        user = self.repository.get_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserResponse.model_validate(user)

    def register_user(self, db: Session, data: UserCreate) -> UserResponse:
        existing_user = self.repository.find_by_identity(db, str(data.email), data.phone, data.student_id)
        if existing_user is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User identity already exists")

        user = self.repository.create_user(
            db,
            name=data.name,
            phone=data.phone,
            email=str(data.email),
            password_hash=hash_password(data.password),
            role=data.role,
            student_id=data.student_id,
        )
        return UserResponse.model_validate(user)

    def update_user(self, db: Session, user_id: int, data: UserUpdate) -> UserResponse:
        user = self.repository.get_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if data.email is not None:
            matching_user = self.repository.get_by_email(db, str(data.email))
            if matching_user is not None and matching_user.id != user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

        if data.phone is not None:
            matching_user = self.repository.get_by_phone(db, data.phone)
            if matching_user is not None and matching_user.id != user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already exists")

        if data.student_id is not None:
            matching_user = self.repository.get_by_student_id(db, data.student_id)
            if matching_user is not None and matching_user.id != user.id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student ID already exists")
        updated_user = self.repository.update_user(db, user, data)
        return UserResponse.model_validate(updated_user)

    def deactivate_user(self, db: Session, user_id: int) -> UserResponse:
        user = self.repository.get_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        deactivated_user = self.repository.deactivate_user(db, user)
        return UserResponse.model_validate(deactivated_user)
