from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.apps.credit_tab.providers import provide_credit_service
from app.apps.credit_tab.schemas import (
    CreditPaymentCreate,
    CreditPaymentResponse,
    CreditTabCreate,
    CreditTabDetailResponse,
    CreditTabResponse,
    DebtReminderSummary,
)
from app.apps.credit_tab.service import CreditService
from app.core.database import get_db
from app.shared.auth import AuthenticatedUser, require_student, require_vendor


router = APIRouter(prefix="/credit", tags=["Credit Tab"])


@router.get("/my", response_model=list[CreditTabResponse])
def get_my_credit_tabs(
    current_user: Annotated[AuthenticatedUser, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CreditService, Depends(provide_credit_service)],
) -> list[CreditTabResponse]:
    return service.fetch_student_tabs(db, current_user.id)


@router.get("/my/unpaid", response_model=list[CreditTabResponse])
def get_my_unpaid_credit_tabs(
    current_user: Annotated[AuthenticatedUser, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CreditService, Depends(provide_credit_service)],
) -> list[CreditTabResponse]:
    return service.fetch_unpaid_tabs(db, current_user.id)


@router.post("/open", response_model=CreditTabResponse, status_code=status.HTTP_201_CREATED)
def open_credit_tab(
    data: CreditTabCreate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CreditService, Depends(provide_credit_service)],
) -> CreditTabResponse:
    return service.open_credit_tab(db, current_user.id, data)


@router.get("/vendor/all", response_model=list[CreditTabResponse])
def get_vendor_credit_tabs(
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CreditService, Depends(provide_credit_service)],
) -> list[CreditTabResponse]:
    return service.fetch_vendor_tabs(db, current_user.id)


@router.post("/pay", response_model=CreditPaymentResponse, status_code=status.HTTP_201_CREATED)
def record_credit_payment(
    data: CreditPaymentCreate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CreditService, Depends(provide_credit_service)],
) -> CreditPaymentResponse:
    return service.record_payment(db, current_user.id, data)


@router.get("/remind/{student_id}", response_model=DebtReminderSummary)
def send_debt_reminder(
    student_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CreditService, Depends(provide_credit_service)],
) -> DebtReminderSummary:
    return service.send_debt_reminder(db, current_user.id, student_id)


@router.get("/{tab_id}", response_model=CreditTabDetailResponse)
def get_credit_tab(
    tab_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[CreditService, Depends(provide_credit_service)],
) -> CreditTabDetailResponse:
    return service.fetch_tab(db, tab_id, current_user.id)
