from fastapi import APIRouter

router = APIRouter(prefix="/idempotency", tags=["Idempotency"])

# This package provides shared idempotency behavior for other apps.
# No public endpoints are exposed by default.
