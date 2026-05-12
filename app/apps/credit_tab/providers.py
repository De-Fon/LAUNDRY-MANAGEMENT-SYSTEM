from typing import Annotated

from fastapi import Depends

from app.apps.credit_tab.repository import CreditRepository
from app.apps.credit_tab.service import CreditService


def provide_credit_repository() -> CreditRepository:
    return CreditRepository()


def provide_credit_service(
    repository: Annotated[CreditRepository, Depends(provide_credit_repository)],
) -> CreditService:
    return CreditService(repository)
