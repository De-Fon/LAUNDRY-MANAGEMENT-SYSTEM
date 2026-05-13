from typing import Annotated

from fastapi import Depends

from app.apps.idempotency.repository import IdempotencyRepository
from app.apps.idempotency.service import IdempotencyService


def provide_idempotency_repository() -> IdempotencyRepository:
    return IdempotencyRepository()


def provide_idempotency_service(
    repository: Annotated[IdempotencyRepository, Depends(provide_idempotency_repository)],
) -> IdempotencyService:
    return IdempotencyService(repository)
