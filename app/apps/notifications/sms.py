from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.core.logger import logger
from app.core.settings import get_settings


@dataclass(frozen=True)
class SMSSendResult:
    success: bool
    provider: str
    status: str
    external_id: str | None = None
    error: str | None = None
    raw_response: dict[str, Any] | None = None


class SMSProvider(Protocol):
    def send_sms(self, to_phone: str, message: str) -> SMSSendResult:
        ...


class AfricaTalkingSandboxSMSProvider:
    provider_name = "africastalking_sandbox"
    endpoint = "https://api.sandbox.africastalking.com/version1/messaging"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.settings = get_settings()
        self.client = client or httpx.Client(timeout=10.0)

    def send_sms(self, to_phone: str, message: str) -> SMSSendResult:
        if not self.settings.sms_enabled:
            logger.info(f"SMS skipped because SMS_ENABLED is false | to={to_phone}")
            return SMSSendResult(
                success=False,
                provider=self.provider_name,
                status="disabled",
                error="SMS is disabled",
            )

        if not self.settings.africastalking_api_key:
            logger.warning(f"SMS skipped because AFRICASTALKING_API_KEY is not configured | to={to_phone}")
            return SMSSendResult(
                success=False,
                provider=self.provider_name,
                status="missing_api_key",
                error="Africa's Talking sandbox API key is not configured",
            )

        payload = {
            "username": self.settings.africastalking_username,
            "to": to_phone,
            "message": message,
        }
        if self.settings.africastalking_sender_id:
            payload["from"] = self.settings.africastalking_sender_id

        try:
            response = self.client.post(
                self.endpoint,
                data=payload,
                headers={
                    "Accept": "application/json",
                    "apiKey": self.settings.africastalking_api_key,
                },
            )
            response.raise_for_status()
            response_data = response.json()
        except Exception as exc:
            logger.error(f"SMS delivery failed | provider={self.provider_name} | to={to_phone} | error={exc}")
            return SMSSendResult(
                success=False,
                provider=self.provider_name,
                status="failed",
                error=str(exc),
            )

        recipient = self._first_recipient(response_data)
        recipient_status = str(recipient.get("status", "sent")) if recipient else "sent"
        external_id = str(recipient.get("messageId")) if recipient and recipient.get("messageId") else None
        success = recipient_status.lower() not in {"failed", "rejected"}

        if success:
            logger.info(
                f"SMS sent | provider={self.provider_name} | to={to_phone} | "
                f"status={recipient_status} | message_id={external_id}"
            )
        else:
            logger.error(
                f"SMS rejected | provider={self.provider_name} | to={to_phone} | "
                f"status={recipient_status} | response={response_data}"
            )

        return SMSSendResult(
            success=success,
            provider=self.provider_name,
            status=recipient_status,
            external_id=external_id,
            raw_response=response_data,
        )

    @staticmethod
    def _first_recipient(response_data: dict[str, Any]) -> dict[str, Any] | None:
        recipients = response_data.get("SMSMessageData", {}).get("Recipients", [])
        if not recipients:
            return None
        recipient = recipients[0]
        return recipient if isinstance(recipient, dict) else None


class SMSService:
    def __init__(self, provider: SMSProvider) -> None:
        self.provider = provider

    def send(self, to_phone: str, message: str) -> SMSSendResult:
        return self.provider.send_sms(to_phone, message)
