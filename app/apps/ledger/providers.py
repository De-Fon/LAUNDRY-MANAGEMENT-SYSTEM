from typing import Annotated

from fastapi import Depends

from app.apps.idempotency.providers import provide_idempotency_service
from app.apps.idempotency.service import IdempotencyService
from app.apps.ledger.repository import LedgerRepository
from app.apps.ledger.service import LedgerService


def provide_ledger_repository() -> LedgerRepository:
    return LedgerRepository()


def provide_ledger_service(
    repository: Annotated[LedgerRepository, Depends(provide_ledger_repository)],
    idempotency_service: Annotated[IdempotencyService, Depends(provide_idempotency_service)],
) -> LedgerService:
    return LedgerService(repository, idempotency_service)
