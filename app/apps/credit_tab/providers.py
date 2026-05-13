from typing import Annotated

from fastapi import Depends

from app.apps.credit_tab.repository import CreditRepository
from app.apps.credit_tab.service import CreditService
from app.apps.idempotency.providers import provide_idempotency_service
from app.apps.idempotency.service import IdempotencyService


def provide_credit_repository() -> CreditRepository:
    return CreditRepository()


def provide_credit_service(
    repository: Annotated[CreditRepository, Depends(provide_credit_repository)],
    idempotency_service: Annotated[IdempotencyService, Depends(provide_idempotency_service)],
) -> CreditService:
    return CreditService(repository, idempotency_service)
