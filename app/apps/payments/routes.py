from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.orm import Session
from app.core.limiter import limiter

from app.apps.payments.providers import provide_payment_service
from app.apps.payments.schemas import (
    DarajaCallbackResponse,
    PaymentCreate,
    PaymentResponse,
    PaymentStatusUpdate,
    STKPushRequest,
    STKPushResponse,
    STKQueryResponse,
)
from app.apps.payments.service import PaymentService
from app.core.database import get_db
from app.shared.auth import AuthenticatedUser, get_current_user, require_vendor


router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("15/minute")
def create_payment(
    request: Request,
    data: PaymentCreate,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PaymentService, Depends(provide_payment_service)],
) -> PaymentResponse:
    return service.create_payment(db, current_user, data)


@router.post("/stk-push", response_model=STKPushResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
def initiate_stk_push(
    request: Request,
    data: STKPushRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PaymentService, Depends(provide_payment_service)],
) -> STKPushResponse:
    return service.initiate_stk_push(db, current_user, data)


@router.get("/me", response_model=list[PaymentResponse])
def get_my_payments(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PaymentService, Depends(provide_payment_service)],
) -> list[PaymentResponse]:
    return service.fetch_my_payments(db, current_user)


@router.get("/status/{checkout_request_id}", response_model=STKQueryResponse)
def query_payment_status(
    checkout_request_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PaymentService, Depends(provide_payment_service)],
) -> STKQueryResponse:
    return service.query_stk_status(db, current_user, checkout_request_id, background_tasks)


@router.post("/callback", response_model=DarajaCallbackResponse)
async def daraja_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PaymentService, Depends(provide_payment_service)],
) -> DarajaCallbackResponse:
    payload = await request.json()
    return service.handle_callback(db, payload, background_tasks)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PaymentService, Depends(provide_payment_service)],
) -> PaymentResponse:
    return service.fetch_payment(db, current_user, payment_id)


@router.patch("/{payment_id}/status", response_model=PaymentResponse, dependencies=[Depends(require_vendor)])
def update_payment_status(
    payment_id: int,
    data: PaymentStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PaymentService, Depends(provide_payment_service)],
) -> PaymentResponse:
    return service.update_payment_status(db, payment_id, data, background_tasks)
