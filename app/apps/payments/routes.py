from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.apps.payments.providers import provide_payment_service
from app.apps.payments.schemas import PaymentCreate, PaymentResponse, PaymentStatusUpdate
from app.apps.payments.service import PaymentService
from app.apps.users.models import User
from app.core.database import get_db
from app.shared.auth import get_current_user, require_vendor


router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    data: PaymentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PaymentService, Depends(provide_payment_service)],
) -> PaymentResponse:
    return service.create_payment(db, current_user, data)


@router.get("/me", response_model=list[PaymentResponse])
def get_my_payments(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PaymentService, Depends(provide_payment_service)],
) -> list[PaymentResponse]:
    return service.fetch_my_payments(db, current_user)


@router.patch("/{payment_id}/status", response_model=PaymentResponse, dependencies=[Depends(require_vendor)])
def update_payment_status(
    payment_id: int,
    data: PaymentStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[PaymentService, Depends(provide_payment_service)],
) -> PaymentResponse:
    return service.update_payment_status(db, payment_id, data)
