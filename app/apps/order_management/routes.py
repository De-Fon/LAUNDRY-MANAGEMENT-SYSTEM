from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter

from app.apps.order_management.providers import provide_order_service
from app.apps.order_management.schemas import OrderCreate, OrderDetailResponse, OrderResponse, OrderStatusUpdate
from app.apps.order_management.service import OrderService
from app.core.database import get_db
from app.shared.auth import AuthenticatedUser, require_student, require_vendor


router = APIRouter(prefix="/orders", tags=["Order Management"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def create_order(
    request: Request,
    data: OrderCreate,
    current_user: Annotated[AuthenticatedUser, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[OrderService, Depends(provide_order_service)],
) -> OrderResponse:
    return service.place_order(db, current_user.id, data)


@router.get("/my", response_model=list[OrderResponse])
def get_my_orders(
    current_user: Annotated[AuthenticatedUser, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[OrderService, Depends(provide_order_service)],
) -> list[OrderResponse]:
    return service.fetch_student_orders(db, current_user.id)


@router.get("/vendor/all", response_model=list[OrderResponse])
def get_vendor_orders(
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[OrderService, Depends(provide_order_service)],
) -> list[OrderResponse]:
    return service.fetch_vendor_orders(db, current_user.id)


@router.patch("/{order_id}/status", response_model=OrderResponse)
@limiter.limit("30/minute")
def update_order_status(
    request: Request,
    background_tasks: BackgroundTasks,
    order_id: int,
    data: OrderStatusUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(require_vendor)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[OrderService, Depends(provide_order_service)],
) -> OrderResponse:
    return service.update_status(db, order_id, data, current_user.id, background_tasks)


@router.get("/{order_code}", response_model=OrderDetailResponse)
@limiter.limit("60/minute")
def get_order(
    request: Request,
    order_code: str,
    current_user: Annotated[AuthenticatedUser, Depends(require_student)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[OrderService, Depends(provide_order_service)],
) -> OrderDetailResponse:
    return service.fetch_order(db, order_code, current_user.id)
