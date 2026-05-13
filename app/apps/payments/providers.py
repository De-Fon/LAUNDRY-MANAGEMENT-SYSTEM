from typing import Annotated

from fastapi import Depends

from app.apps.payments.repository import PaymentRepository
from app.apps.payments.service import PaymentService


def provide_payment_repository() -> PaymentRepository:
    return PaymentRepository()


def provide_payment_service(
    repository: Annotated[PaymentRepository, Depends(provide_payment_repository)],
) -> PaymentService:
    return PaymentService(repository)
