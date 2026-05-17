from fastapi import BackgroundTasks, HTTPException, status
from app.core.logger import logger
from sqlalchemy.orm import Session

from app.apps.notifications.email import EmailService
from app.apps.notifications.email.templates import (
    account_notification_template,
    rate_card_template,
    transaction_receipt_template,
)
from app.apps.notifications.models import NotificationChannel
from app.apps.notifications.repository import NotificationRepository
from app.apps.notifications.schemas import NotificationCreate, NotificationResponse
from app.apps.notifications.sms import SMSService
from app.apps.users.models import RoleEnum, User

PICKUP_CREATED_SMS = "Your laundry pickup request has been received."
ORDER_STATUS_CHANGED_SMS = "Your laundry order status changed to: {status}"
LAUNDRY_COMPLETED_SMS = "Your laundry is ready for pickup."


class NotificationService:
    def __init__(
        self,
        repository: NotificationRepository,
        sms_service: SMSService | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self.repository = repository
        self.sms_service = sms_service
        self.email_service = email_service

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

        if self.email_service is None:
            logger.error(f"Email background task failed | Email service not configured | id={notification_id}")
            self.repository.mark_failed(db, notification)
            return

        result = self.email_service.send(
            to_email=to_email,
            subject=notification.subject,
            html_body=notification.message,
        )

        if result.success:
            self.repository.mark_sent(db, notification)
            logger.info(
                f"Email background task completed | "
                f"notification_id={notification_id} | to={to_email} | provider={result.provider}"
            )
        else:
            self.repository.mark_failed(db, notification)
            logger.error(
                f"Email background task failed | "
                f"notification_id={notification_id} | to={to_email} | "
                f"provider={result.provider} | status={result.status} | error={result.error}"
            )

    def queue_email_notification(
        self,
        db: Session,
        background_tasks: BackgroundTasks | None,
        *,
        user_id: int,
        subject: str,
        message: str,
    ) -> NotificationResponse | None:
        try:
            user = self.repository.get_user(db, user_id)
            if user is None:
                logger.error(f"Email notification skipped | user not found | user_id={user_id}")
                return None

            notification = self.repository.create_notification(
                db,
                user_id=user_id,
                channel=NotificationChannel.email,
                subject=subject,
                message=message,
            )
            if background_tasks is None:
                self.dispatch_email_background(db, notification.id, user.email)
            else:
                background_tasks.add_task(self.dispatch_email_background, db, notification.id, user.email)

            logger.info(f"Email notification queued | notification_id={notification.id} | user_id={user_id}")
            return NotificationResponse.model_validate(notification)
        except Exception as exc:
            db.rollback()
            logger.error(f"Email notification queue failed | user_id={user_id} | error={exc}")
            return None

    def dispatch_sms_background(
        self,
        db: Session,
        notification_id: int,
        to_phone: str,
    ) -> None:
        notification = self.repository.get_by_id(db, notification_id)
        if notification is None:
            logger.error(f"SMS background task failed | notification not found | id={notification_id}")
            return

        if self.sms_service is None:
            logger.error(f"SMS background task failed | SMS service not configured | id={notification_id}")
            self.repository.mark_failed(db, notification)
            return

        result = self.sms_service.send(to_phone, notification.message)
        if result.success:
            self.repository.mark_sent(db, notification)
            logger.info(
                f"SMS background task completed | notification_id={notification_id} | "
                f"to={to_phone} | provider={result.provider}"
            )
            return

        self.repository.mark_failed(db, notification)
        logger.error(
            f"SMS background task failed | notification_id={notification_id} | "
            f"to={to_phone} | provider={result.provider} | status={result.status} | error={result.error}"
        )

    def queue_sms_notification(
        self,
        db: Session,
        background_tasks: BackgroundTasks | None,
        *,
        user_id: int,
        subject: str,
        message: str,
    ) -> NotificationResponse | None:
        try:
            user = self.repository.get_user(db, user_id)
            if user is None:
                logger.error(f"SMS notification skipped | user not found | user_id={user_id}")
                return None

            notification = self.repository.create_notification(
                db,
                user_id=user_id,
                channel=NotificationChannel.sms,
                subject=subject,
                message=message,
            )
            if background_tasks is None:
                self.dispatch_sms_background(db, notification.id, user.phone)
            else:
                background_tasks.add_task(self.dispatch_sms_background, db, notification.id, user.phone)

            logger.info(f"SMS notification queued | notification_id={notification.id} | user_id={user_id}")
            return NotificationResponse.model_validate(notification)
        except Exception as exc:
            db.rollback()
            logger.error(f"SMS notification queue failed | user_id={user_id} | error={exc}")
            return None

    def notify_pickup_created(
        self,
        db: Session,
        background_tasks: BackgroundTasks | None,
        *,
        user_id: int,
    ) -> None:
        self.queue_sms_notification(
            db,
            background_tasks,
            user_id=user_id,
            subject="Laundry pickup received",
            message=PICKUP_CREATED_SMS,
        )

    def notify_order_status_changed(
        self,
        db: Session,
        background_tasks: BackgroundTasks | None,
        *,
        user_id: int,
        order_status: str,
    ) -> None:
        self.queue_sms_notification(
            db,
            background_tasks,
            user_id=user_id,
            subject="Laundry order update",
            message=ORDER_STATUS_CHANGED_SMS.format(status=order_status),
        )

    def notify_laundry_completed(
        self,
        db: Session,
        background_tasks: BackgroundTasks | None,
        *,
        user_id: int,
    ) -> None:
        self.queue_sms_notification(
            db,
            background_tasks,
            user_id=user_id,
            subject="Laundry ready for pickup",
            message=LAUNDRY_COMPLETED_SMS,
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

        notification = self.queue_email_notification(
            db,
            background_tasks,
            user_id=student_id,
            subject=subject,
            message=order_ready_template(student_name, order_code),
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
        self.queue_email_notification(
            db,
            background_tasks,
            user_id=student_id,
            subject=f"Payment Receipt — {order_code}",
            message=transaction_receipt_template(
                order_number=order_code,
                services=["Laundry service"],
                total=amount_paid,
                payment_status="completed" if outstanding_balance == 0 else "partial",
                timestamp=None,
            ),
        )

        logger.info(
            f"Payment receipt email queued | order_code={order_code} | "
            f"amount={amount_paid} | to={student_email}"
        )

    def send_transaction_receipt_email(
        self,
        db: Session,
        background_tasks: BackgroundTasks | None,
        *,
        student_id: int,
        order_number: str,
        services: list[str],
        total: float,
        payment_status: str,
        timestamp,
    ) -> None:
        self.queue_email_notification(
            db,
            background_tasks,
            user_id=student_id,
            subject="Laundry Transaction Receipt",
            message=transaction_receipt_template(
                order_number=order_number,
                services=services,
                total=total,
                payment_status=payment_status,
                timestamp=timestamp,
            ),
        )

    def send_rate_card_email(
        self,
        db: Session,
        background_tasks: BackgroundTasks | None,
        *,
        user_id: int,
        services: list[tuple[str, float]],
    ) -> None:
        self.queue_email_notification(
            db,
            background_tasks,
            user_id=user_id,
            subject="Laundry Service Rate Card",
            message=rate_card_template(services),
        )

    def send_account_notification_email(
        self,
        db: Session,
        background_tasks: BackgroundTasks | None,
        *,
        user_id: int,
        student_name: str,
        message: str,
    ) -> None:
        self.queue_email_notification(
            db,
            background_tasks,
            user_id=user_id,
            subject="Account Notification",
            message=account_notification_template(student_name=student_name, message=message),
        )
