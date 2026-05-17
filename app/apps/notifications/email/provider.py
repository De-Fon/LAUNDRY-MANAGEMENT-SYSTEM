from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class EmailAttachment:
    filename: str
    content: str


@dataclass(frozen=True)
class EmailSendResult:
    success: bool
    provider: str
    status: str
    external_id: str | None = None
    error: str | None = None
    raw_response: dict[str, Any] | None = None


class EmailProvider(Protocol):
    def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        attachments: list[EmailAttachment] | None = None,
    ) -> EmailSendResult:
        ...
