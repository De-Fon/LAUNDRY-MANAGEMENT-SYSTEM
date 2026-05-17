from datetime import UTC, datetime

from sqlalchemy import select

from app.apps.notifications.email import EmailSendResult, EmailService, ResendEmailProvider
from app.apps.notifications.email.templates import rate_card_template, transaction_receipt_template
from app.apps.notifications.models import Notification, NotificationChannel, NotificationStatus
from app.apps.notifications.repository import NotificationRepository
from app.apps.notifications.service import NotificationService


class FakeResendEmails:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, params: dict) -> dict:
        self.sent.append(params)
        return {"id": "email_test_123"}


class FakeResendClient:
    def __init__(self) -> None:
        self.api_key = None
        self.Emails = FakeResendEmails()


class FakeEmailProvider:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send_email(self, *, to_email: str, subject: str, html_body: str, attachments=None) -> EmailSendResult:
        self.sent.append(
            {
                "to_email": to_email,
                "subject": subject,
                "html_body": html_body,
                "attachments": attachments,
            }
        )
        return EmailSendResult(success=True, provider="fake", status="sent", external_id="fake_email_1")


def test_resend_provider_uses_official_sdk_send_method():
    client = FakeResendClient()
    provider = ResendEmailProvider(resend_client=client)
    original_email_enabled = provider.settings.email_enabled
    original_api_key = provider.settings.resend_api_key
    original_email_from = provider.settings.email_from
    provider.settings.email_enabled = True
    provider.settings.resend_api_key = "re_test"
    provider.settings.email_from = "noreply@example.com"

    try:
        result = provider.send_email(
            to_email="student@test.com",
            subject="Account Notification",
            html_body="<p>Hello</p>",
        )
    finally:
        provider.settings.email_enabled = original_email_enabled
        provider.settings.resend_api_key = original_api_key
        provider.settings.email_from = original_email_from

    assert result.success is True
    assert client.api_key == "re_test"
    assert client.Emails.sent[0]["to"] == ["student@test.com"]
    assert client.Emails.sent[0]["subject"] == "Account Notification"
    assert client.Emails.sent[0]["html"] == "<p>Hello</p>"


def test_notification_service_queues_email_with_mock_provider(db_session, test_student):
    provider = FakeEmailProvider()
    service = NotificationService(NotificationRepository(), email_service=EmailService(provider))

    service.send_account_notification_email(
        db_session,
        None,
        user_id=test_student.id,
        student_name=test_student.name,
        message="Your account has been created successfully.",
    )

    notification = db_session.scalar(select(Notification).where(Notification.user_id == test_student.id))
    assert notification is not None
    assert notification.channel == NotificationChannel.email
    assert notification.status == NotificationStatus.sent
    assert notification.subject == "Account Notification"
    assert provider.sent[0]["to_email"] == test_student.email


def test_transaction_receipt_template_contains_required_fields():
    html = transaction_receipt_template(
        order_number="ORD-123",
        services=["Wash", "Dry"],
        total=250.0,
        payment_status="success",
        timestamp=datetime(2026, 5, 17, 12, 0, tzinfo=UTC),
    )

    assert "Laundry Transaction Receipt" in html
    assert "ORD-123" in html
    assert "Wash" in html
    assert "Dry" in html
    assert "KES 250.00" in html
    assert "success" in html


def test_rate_card_template_contains_service_pricing():
    html = rate_card_template([("Wash", 100.0), ("Iron", 50.0)])

    assert "Laundry Service Rate Card" in html
    assert "Wash" in html
    assert "KES 100.00" in html
    assert "Iron" in html
    assert "KES 50.00" in html
