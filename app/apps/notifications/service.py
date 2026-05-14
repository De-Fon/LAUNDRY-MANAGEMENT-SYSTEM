from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.notifications.models import NotificationChannel
from app.apps.notifications.repository import NotificationRepository
from app.apps.notifications.schemas import NotificationCreate, NotificationResponse
from app.apps.users.models import RoleEnum, User


class NotificationService:
    def __init__(self, repository: NotificationRepository) -> None:
        self.repository = repository

    def create_notification(self, db: Session, data: NotificationCreate) -> NotificationResponse:
        if self.repository.get_user(db, data.user_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        notification = self.repository.create_notification(
            db,
            user_id=data.user_id,
            channel=data.channel,
            subject=data.subject,
            message=data.message,
        )
        if data.channel == NotificationChannel.in_app:
            notification = self.repository.mark_sent(db, notification)
        return NotificationResponse.model_validate(notification)

    def fetch_my_notifications(self, db: Session, current_user: User) -> list[NotificationResponse]:
        notifications = self.repository.list_for_user(db, current_user.id)
        return [NotificationResponse.model_validate(notification) for notification in notifications]

    def mark_read(self, db: Session, current_user: User, notification_id: int) -> NotificationResponse:
        notification = self.repository.get_by_id(db, notification_id)
        if notification is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

        if notification.user_id != current_user.id and current_user.role != RoleEnum.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Notification is not available")

        notification = self.repository.mark_read(db, notification)
        return NotificationResponse.model_validate(notification)
