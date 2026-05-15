from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.apps.notifications.models import Notification, NotificationChannel, NotificationStatus
from app.apps.users.models import User
from app.core.logger import logger

class NotificationRepository:
    def get_user(self, db: Session, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id, User.is_active.is_(True))
        return db.scalar(statement)

    def get_by_id(self, db: Session, notification_id: int) -> Notification | None:
        statement = select(Notification).where(Notification.id == notification_id)
        return db.scalar(statement)

    def list_for_user(self, db: Session, user_id: int) -> list[Notification]:
        statement = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        return list(db.scalars(statement).all())

    def create_notification(
        self,
        db: Session,
        *,
        user_id: int,
        channel: NotificationChannel,
        subject: str,
        message: str,
    ) -> Notification:
        notification = Notification(user_id=user_id, channel=channel, subject=subject, message=message)
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    def mark_sent(self, db: Session, notification: Notification) -> Notification:
        notification.status = NotificationStatus.sent
        notification.sent_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
        return notification

    def mark_read(self, db: Session, notification: Notification) -> Notification:
        notification.status = NotificationStatus.read
        notification.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(notification)
        return notification

    def mark_failed(
        self,
        db: Session,
        notification: Notification,
        error_detail: str | None = None,
    ) -> Notification:
        notification.status = NotificationStatus.failed
        db.commit()
        db.refresh(notification)
        logger.info(
            f"Notification marked failed | id={notification.id} | "
            f"channel={notification.channel}"
        )
        return notification
