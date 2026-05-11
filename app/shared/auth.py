from fastapi import HTTPException, status


try:
    from app.apps.auth.providers import require_vendor
except ModuleNotFoundError:

    def require_vendor() -> None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Vendor authorization is not configured yet",
        )
