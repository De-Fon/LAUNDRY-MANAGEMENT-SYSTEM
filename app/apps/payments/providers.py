from typing import Annotated

from fastapi import Depends

from app.apps.idempotency.providers import provide_idempotency_service
from app.apps.idempotency.service import IdempotencyService
from app.apps.payments.repository import PaymentRepository
from app.apps.payments.service import PaymentService


def provide_payment_repository() -> PaymentRepository:
    return PaymentRepository()


def provide_payment_service(
    repository: Annotated[PaymentRepository, Depends(provide_payment_repository)],
    idempotency_service: Annotated[IdempotencyService, Depends(provide_idempotency_service)],
) -> PaymentService:
    return PaymentService(repository, idempotency_service)
