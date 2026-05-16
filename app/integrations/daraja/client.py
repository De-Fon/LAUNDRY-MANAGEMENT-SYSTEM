from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.settings import Settings


SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"


class DarajaAPIError(RuntimeError):
    def __init__(self, message: str, response_payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.response_payload = response_payload or {}


@dataclass
class DarajaToken:
    access_token: str
    expires_at: datetime


class DarajaClient:
    """Small Daraja API client. Business decisions stay in PaymentService."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = PRODUCTION_BASE_URL if settings.daraja_environment == "production" else SANDBOX_BASE_URL
        self._token: DarajaToken | None = None

    def initiate_stk_push(
        self,
        *,
        phone_number: str,
        amount: int,
        account_reference: str,
        transaction_desc: str,
        callback_url: str,
    ) -> dict[str, Any]:
        timestamp = self._timestamp()
        payload = {
            "BusinessShortCode": self.settings.daraja_business_short_code,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.settings.daraja_business_short_code,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc,
        }
        return self._post("/mpesa/stkpush/v1/processrequest", payload)

    def query_stk_push(self, *, checkout_request_id: str) -> dict[str, Any]:
        timestamp = self._timestamp()
        payload = {
            "BusinessShortCode": self.settings.daraja_business_short_code,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }
        return self._post("/mpesa/stkpushquery/v1/query", payload)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._access_token()}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=self.settings.daraja_request_timeout_seconds) as client:
                response = client.post(f"{self.base_url}{path}", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise DarajaAPIError("Daraja returned an unsuccessful HTTP response", self._safe_json(exc.response)) from exc
        except httpx.HTTPError as exc:
            raise DarajaAPIError("Daraja request failed before a valid response was received") from exc

        if data.get("errorCode"):
            raise DarajaAPIError(str(data.get("errorMessage", "Daraja API error")), data)
        return data

    def _access_token(self) -> str:
        if self._token is not None and self._token.expires_at > datetime.now(UTC) + timedelta(seconds=30):
            return self._token.access_token

        if not self.settings.daraja_consumer_key or not self.settings.daraja_consumer_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Daraja credentials are not configured",
            )

        credentials = f"{self.settings.daraja_consumer_key}:{self.settings.daraja_consumer_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers = {"Authorization": f"Basic {encoded_credentials}"}
        try:
            with httpx.Client(timeout=self.settings.daraja_request_timeout_seconds) as client:
                response = client.get(
                    f"{self.base_url}/oauth/v1/generate",
                    params={"grant_type": "client_credentials"},
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise DarajaAPIError("Daraja OAuth rejected the configured credentials", self._safe_json(exc.response)) from exc
        except httpx.HTTPError as exc:
            raise DarajaAPIError("Daraja OAuth request failed") from exc

        access_token = data.get("access_token")
        if not access_token:
            raise DarajaAPIError("Daraja OAuth response did not contain an access token", data)

        expires_in = int(data.get("expires_in", 3599))
        self._token = DarajaToken(
            access_token=access_token,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
        )
        return access_token

    def _password(self, timestamp: str) -> str:
        if not self.settings.daraja_passkey:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Daraja passkey is not configured",
            )
        raw_password = f"{self.settings.daraja_business_short_code}{self.settings.daraja_passkey}{timestamp}"
        return base64.b64encode(raw_password.encode()).decode()

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any]:
        try:
            return response.json()
        except ValueError:
            return {"body": response.text}
