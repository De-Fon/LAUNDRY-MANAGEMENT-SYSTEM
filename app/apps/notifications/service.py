from fastapi import BackgroundTasks, HTTPException, status
from app.core.logger import logger
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

    def dispatch_email_background(
        self,
        db: Session,
        notification_id: int,
        to_email: str,
    ) -> None:
        """
        Designed to run as a FastAPI BackgroundTask.
        Executes AFTER the HTTP response is already sent.
        Fetches notification, sends email, updates status.
        Never raises — logs all errors instead.
        """
        from app.core.email import send_email

        notification = self.repository.get_by_id(db, notification_id)
        if notification is None:
            logger.error(
                f"Email background task failed — notification not found | "
                f"id={notification_id}"
            )
            return

        logger.info(
            f"Email background task started | "
            f"notification_id={notification_id} | to={to_email}"
        )

        success = send_email(
            to_email=to_email,
            subject=notification.subject,
            html_body=f"<p>{notification.message}</p>",
        )

        if success:
            self.repository.mark_sent(db, notification)
            logger.info(
                f"Email background task completed | "
                f"notification_id={notification_id} | to={to_email}"
            )
        else:
            self.repository.mark_failed(db, notification)
            logger.error(
                f"Email background task failed | "
                f"notification_id={notification_id} | to={to_email}"
            )

    def notify_order_ready(
        self,
        db: Session,
        background_tasks: BackgroundTasks,
        order_id: int,
        student_id: int,
        student_email: str,
        student_name: str,
        order_code: str,
    ) -> dict:
        """
        Called when vendor marks order as READY.
        Creates email notification record in DB.
        Sends actual email in background — never blocks response.
        """
        from app.core.email_templates import order_ready_template

        subject = "Your laundry is ready for pickup!"
        html_body = order_ready_template(student_name, order_code)

        notification = self.repository.create_notification(
            db,
            user_id=student_id,
            channel=NotificationChannel.email,
            subject=subject,
            message=f"Hi {student_name}, your order {order_code} is ready.",
        )

        background_tasks.add_task(
            self.dispatch_email_background,
            db,
            notification.id,
            student_email,
        )

        logger.info(
            f"Order ready email queued | order_id={order_id} | "
            f"order_code={order_code} | to={student_email}"
        )

        return {
            "message": "Email notification queued",
            "channel": "email",
            "order_id": order_id,
            "order_code": order_code,
        }

    def send_payment_receipt_email(
        self,
        db: Session,
        background_tasks: BackgroundTasks,
        student_id: int,
        student_email: str,
        student_name: str,
        order_code: str,
        amount_paid: float,
        outstanding_balance: float,
    ) -> None:
        """
        Called after a payment is recorded.
        Sends receipt email in background.
        """
        from app.core.email_templates import payment_receipt_template

        subject = f"Payment Receipt — {order_code}"
        html_body = payment_receipt_template(
            student_name, order_code, amount_paid, outstanding_balance
        )

        notification = self.repository.create_notification(
            db,
            user_id=student_id,
            channel=NotificationChannel.email,
            subject=subject,
            message=f"Payment of KES {amount_paid} received for {order_code}.",
        )

        background_tasks.add_task(
            self.dispatch_email_background,
            db,
            notification.id,
            student_email,
        )

        logger.info(
            f"Payment receipt email queued | order_code={order_code} | "
            f"amount={amount_paid} | to={student_email}"
        )
