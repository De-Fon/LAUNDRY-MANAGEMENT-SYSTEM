from __future__ import annotations

from typing import Any

import resend

from app.apps.notifications.email.provider import EmailAttachment, EmailProvider, EmailSendResult
from app.core.logger import logger
from app.core.settings import get_settings


class ResendEmailProvider:
    provider_name = "resend"

    def __init__(self, resend_client: Any | None = None) -> None:
        self.settings = get_settings()
        self.resend_client = resend_client or resend

    def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> EmailSendResult:
        if not self.settings.email_enabled:
            logger.info(f"Email skipped because EMAIL_ENABLED is false | to={to_email}")
            return EmailSendResult(
                success=False,
                provider=self.provider_name,
                status="disabled",
                error="Email is disabled",
            )

        if not self.settings.resend_api_key:
            logger.warning(f"Email skipped because RESEND_API_KEY is not configured | to={to_email}")
            return EmailSendResult(
                success=False,
                provider=self.provider_name,
                status="missing_api_key",
                error="Resend API key is not configured",
            )

        from_email = self.settings.email_from or self.settings.resend_from_email
        params: resend.Emails.SendParams = {
            "from": f"{self.settings.resend_from_name} <{from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        if attachments:
            params["attachments"] = [
                {"filename": attachment.filename, "content": attachment.content}
                for attachment in attachments
            ]

        try:
            self.resend_client.api_key = self.settings.resend_api_key
            response = self.resend_client.Emails.send(params)
        except Exception as exc:
            logger.error(f"Email delivery failed | provider=resend | to={to_email} | subject={subject} | error={exc}")
            return EmailSendResult(
                success=False,
                provider=self.provider_name,
                status="failed",
                error=str(exc),
            )

        external_id = response.get("id") if isinstance(response, dict) else None
        logger.info(f"Email sent | provider=resend | to={to_email} | subject={subject} | resend_id={external_id}")
        return EmailSendResult(
            success=True,
            provider=self.provider_name,
            status="sent",
            external_id=external_id,
            raw_response=response if isinstance(response, dict) else None,
        )


class EmailService:
    def __init__(self, provider: EmailProvider) -> None:
        self.provider = provider

    def send(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> EmailSendResult:
        return self.provider.send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
            attachments=attachments,
        )
