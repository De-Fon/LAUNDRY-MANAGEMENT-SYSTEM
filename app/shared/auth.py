from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    role: str


try:
    from app.apps.auth.providers import require_student, require_vendor
except ModuleNotFoundError:

    def require_student() -> AuthenticatedUser:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Student authorization is not configured yet",
        )

    def require_vendor() -> AuthenticatedUser:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Vendor authorization is not configured yet",
        )
