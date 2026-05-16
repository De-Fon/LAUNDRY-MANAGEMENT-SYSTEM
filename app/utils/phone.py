import re

from fastapi import HTTPException, status


KENYAN_MSISDN_RE = re.compile(r"^(?:254|0)?(7\d{8}|1\d{8})$")


def normalize_kenyan_msisdn(phone_number: str) -> str:
    cleaned = re.sub(r"[\s()+-]", "", phone_number.strip())
    match = KENYAN_MSISDN_RE.fullmatch(cleaned)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number must be a valid Kenyan Safaricom-style MSISDN",
        )
    return f"254{match.group(1)}"
