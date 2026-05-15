import resend
from app.core.settings import get_settings
from app.core.logger import logger


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
) -> bool:
    """
    Sends a transactional email via Resend SDK.
    Returns True on success, False on failure.
    Never raises — always returns bool.
    Caller decides what to do with the result.
    """
    settings = get_settings()

    if not settings.resend_api_key:
        logger.warning(
            f"Email skipped — RESEND_API_KEY not configured | to={to_email}"
        )
        return False

    try:
        resend.api_key = settings.resend_api_key

        params = {
            "from": f"{settings.resend_from_name} <{settings.resend_from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }

        response = resend.Emails.send(params)
        logger.info(
            f"Email sent | to={to_email} | "
            f"subject={subject} | resend_id={response.get('id')}"
        )
        return True

    except Exception as e:
        logger.error(
            f"Email delivery failed | to={to_email} | "
            f"subject={subject} | error={e}"
        )
        return False
