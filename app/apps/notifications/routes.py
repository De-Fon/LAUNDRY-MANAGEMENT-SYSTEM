from typing import Annotated

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.limiter import limiter

from app.apps.notifications.providers import provide_notification_service
from app.apps.notifications.schemas import NotificationCreate, NotificationResponse
from app.apps.notifications.service import NotificationService
from app.core.database import get_db
from app.shared.auth import AuthenticatedUser, get_current_user, require_admin, require_vendor


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("", response_model=NotificationResponse, dependencies=[Depends(require_admin)])
def create_notification(
    data: NotificationCreate,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> NotificationResponse:
    return service.create_notification(db, data)


@router.get("/me", response_model=list[NotificationResponse])
def get_my_notifications(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> list[NotificationResponse]:
    return service.fetch_my_notifications(db, current_user)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> NotificationResponse:
    return service.mark_read(db, current_user, notification_id)


@router.post(
    "/notify-ready/{order_id}",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_vendor)],
)
@limiter.limit("10/minute")
def notify_order_ready(
    request: Request,
    order_id: int,
    background_tasks: BackgroundTasks,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[NotificationService, Depends(provide_notification_service)],
) -> dict:
    """
    Vendor triggers this when order status becomes READY.
    Sends email to student in background.
    Returns 202 Accepted immediately — does not wait for email delivery.
    """
    from app.apps.order_management.repository import OrderRepository
    from app.apps.users.repository import UserRepository

    order = OrderRepository().get_order_by_id_for_update(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status.value.upper() != "READY":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only notify when order status is READY"
        )

    student = UserRepository().get_by_id(db, order.student_id)
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    if not student.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student has no email address on record"
        )

    return service.notify_order_ready(
        db=db,
        background_tasks=background_tasks,
        order_id=order_id,
        student_id=student.id,
        student_email=student.email,
        student_name=getattr(student, "name", None) or student.email,
        order_code=order.order_code,
    )
