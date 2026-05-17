from typing import Annotated

from fastapi import Depends

from app.apps.notifications.email import EmailProvider, EmailService, ResendEmailProvider
from app.apps.notifications.repository import NotificationRepository
from app.apps.notifications.service import NotificationService
from app.apps.notifications.sms import AfricaTalkingSandboxSMSProvider, SMSProvider, SMSService


def provide_notification_repository() -> NotificationRepository:
    return NotificationRepository()


def provide_sms_provider() -> SMSProvider:
    return AfricaTalkingSandboxSMSProvider()


def provide_sms_service(
    provider: Annotated[SMSProvider, Depends(provide_sms_provider)],
) -> SMSService:
    return SMSService(provider)


def provide_email_provider() -> EmailProvider:
    return ResendEmailProvider()


def provide_email_service(
    provider: Annotated[EmailProvider, Depends(provide_email_provider)],
) -> EmailService:
    return EmailService(provider)


def provide_notification_service(
    repository: Annotated[NotificationRepository, Depends(provide_notification_repository)],
    sms_service: Annotated[SMSService, Depends(provide_sms_service)],
    email_service: Annotated[EmailService, Depends(provide_email_service)],
) -> NotificationService:
    return NotificationService(repository, sms_service, email_service)
