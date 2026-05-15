from typing import Annotated

from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter

from app.apps.ledger.providers import provide_ledger_service
from app.apps.ledger.schemas import (
    LedgerAccountCreate,
    LedgerAccountDetailResponse,
    LedgerAccountResponse,
    LedgerAdjustmentCreate,
    LedgerAuditLogResponse,
    LedgerReverseCreate,
    LedgerSummaryResponse,
    LedgerTransactionCreate,
    LedgerTransactionResponse,
)
from app.apps.ledger.service import LedgerService
from app.core.database import get_db
from app.shared.auth import AuthenticatedUser, require_student, require_vendor


router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.get("/my", response_model=LedgerAccountDetailResponse)
def get_my_ledger(
    current_user: Annotated[AuthenticatedUser, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LedgerService, Depends(provide_ledger_service)],
    vendor_id: int | None = Query(default=None),
) -> LedgerAccountDetailResponse:
    return service.fetch_account(db, current_user.id, vendor_id)


@router.get("/my/summary", response_model=LedgerSummaryResponse)
def get_my_ledger_summary(
    current_user: Annotated[AuthenticatedUser, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LedgerService, Depends(provide_ledger_service)],
    vendor_id: int | None = Query(default=None),
) -> LedgerSummaryResponse:
    return service.fetch_account_summary(db, current_user.id, vendor_id)


@router.post("/accounts", response_model=LedgerAccountResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def create_ledger_account(
    request: Request,
    data: LedgerAccountCreate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LedgerService, Depends(provide_ledger_service)],
) -> LedgerAccountResponse:
    return service.open_ledger_account(db, LedgerAccountCreate(student_id=data.student_id, vendor_id=current_user.id))


@router.post("/transactions", response_model=LedgerTransactionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def create_ledger_transaction(
    request: Request,
    data: LedgerTransactionCreate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LedgerService, Depends(provide_ledger_service)],
) -> LedgerTransactionResponse:
    return service.record_transaction(db, data, current_user.id)


@router.post("/transactions/reverse", response_model=LedgerTransactionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def reverse_ledger_transaction(
    request: Request,
    data: LedgerReverseCreate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LedgerService, Depends(provide_ledger_service)],
) -> LedgerTransactionResponse:
    return service.reverse_transaction(db, data.reference_code, current_user.id, data.reason)


@router.post("/adjust", response_model=LedgerTransactionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def apply_ledger_adjustment(
    request: Request,
    data: LedgerAdjustmentCreate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LedgerService, Depends(provide_ledger_service)],
) -> LedgerTransactionResponse:
    return service.apply_adjustment(db, data.model_copy(update={"performed_by": current_user.id}))


@router.get("/accounts/{student_id}", response_model=LedgerAccountDetailResponse)
def get_student_ledger(
    student_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LedgerService, Depends(provide_ledger_service)],
) -> LedgerAccountDetailResponse:
    return service.fetch_account(db, student_id, current_user.id)


@router.get("/audit/{account_id}", response_model=list[LedgerAuditLogResponse])
def get_ledger_audit_logs(
    account_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LedgerService, Depends(provide_ledger_service)],
) -> list[LedgerAuditLogResponse]:
    return service.fetch_audit_logs(db, account_id, current_user.id)
