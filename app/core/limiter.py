from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.logger import logger
from app.core.settings import get_settings

settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    # Uses client IP by default
    # get_remote_address is imported from slowapi.util
    storage_uri=settings.redis_url,
    # Stores rate limit counters in Redis
    # Each IP gets its own counter per endpoint
)


async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """
    Custom 429 response.
    Replaces SlowAPI default with our consistent error format.
    """
    logger.warning(
        f"Rate limit exceeded | "
        f"path={request.url.path} | "
        f"method={request.method} | "
        f"client={get_remote_address(request)}"
    )
    return JSONResponse(
        status_code=429,
        content={
            "error": True,
            "status_code": 429,
            "message": "Too many requests. Please slow down.",
            "detail": str(exc.detail),
            "hint": "Rate limits reset automatically. Try again shortly.",
        },
        headers={
            "Retry-After": "60",
        },
    )
