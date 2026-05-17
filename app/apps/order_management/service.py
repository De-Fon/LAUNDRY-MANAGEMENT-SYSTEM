from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.apps.catalog.repository import CatalogRepository
from app.apps.notifications.service import NotificationService
from app.apps.order_management.models import Order, OrderStatus, OrderStatusLog, VALID_TRANSITIONS
from app.apps.order_management.repository import OrderRepository
from app.apps.order_management.schemas import (
    OrderCreate,
    OrderDetailResponse,
    OrderResponse,
    OrderStatusLogResponse,
    OrderStatusUpdate,
)
from app.apps.pricing.repository import PricingRepository
from app.core.logger import logger
from app.core.pricing import calculate_final_price

class OrderService:
    def __init__(
        self,
        order_repository: OrderRepository,
        catalog_repository: CatalogRepository,
        pricing_repository: PricingRepository,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.order_repository = order_repository
        self.catalog_repository = catalog_repository
        self.pricing_repository = pricing_repository
        self.notification_service = notification_service

    def place_order(self, db: Session, student_id: int, data: OrderCreate) -> OrderResponse:
        service_item = self.catalog_repository.get_item_by_id(db, data.service_item_id)
        if service_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")

        wash_type = self.pricing_repository.get_wash_type_by_name(db, data.wash_type)
        if wash_type is None or not wash_type.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wash type not found")

        item_price = calculate_final_price(service_item.base_price, wash_type.price_multiplier)
        total_price = round(item_price * data.quantity, 2)

        order = self.order_repository.create_order(
            db,
            Order(
                order_code=f"ORD-{uuid4().hex[:8].upper()}",
                student_id=student_id,
                vendor_id=data.vendor_id,
                service_item_id=data.service_item_id,
                wash_type=data.wash_type,
                quantity=data.quantity,
                total_price=total_price,
                special_instructions=data.special_instructions,
            ),
        )
        return OrderResponse.model_validate(order)

    def fetch_order(self, db: Session, order_code: str, student_id: int | None = None) -> OrderDetailResponse:
        order = self.order_repository.get_order_by_code(db, order_code)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        if student_id is not None and order.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own orders")

        status_history = self.order_repository.get_status_logs(db, order.id)
        return OrderDetailResponse(
            **OrderResponse.model_validate(order).model_dump(),
            status_history=[OrderStatusLogResponse.model_validate(log) for log in status_history],
        )

    def fetch_student_orders(self, db: Session, student_id: int) -> list[OrderResponse]:
        return [OrderResponse.model_validate(order) for order in self.order_repository.get_orders_by_student(db, student_id)]

    def fetch_vendor_orders(self, db: Session, vendor_id: int) -> list[OrderResponse]:
        return [OrderResponse.model_validate(order) for order in self.order_repository.get_orders_by_vendor(db, vendor_id)]

    def update_status(
        self,
        db: Session,
        order_id: int,
        status_update: OrderStatusUpdate,
        changed_by: int,
        background_tasks: BackgroundTasks | None = None,
    ) -> OrderResponse:
        order = self.order_repository.get_order_by_id_for_update(db, order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

        if order.vendor_id != changed_by:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own orders")

        if VALID_TRANSITIONS.get(order.status) != status_update.status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status transition")

        updated_order = self.order_repository.apply_status_transition(
            db,
            order,
            status_update.status,
            OrderStatusLog(
                order_id=order_id,
                previous_status=order.status,
                new_status=status_update.status,
                changed_by=changed_by,
                note=status_update.note,
            ),
        )
        logger.info(
            "order_status_change | "
            f"order_id={order.id} | "
            f"order_code={order.order_code} | "
            f"previous={order.status.value} | "
            f"new={status_update.status.value} | "
            f"changed_by={changed_by}"
        )
        if self.notification_service is not None:
            self.notification_service.notify_order_status_changed(
                db,
                background_tasks,
                user_id=updated_order.student_id,
                order_status=status_update.status.value,
            )
            if status_update.status == OrderStatus.READY:
                self.notification_service.notify_laundry_completed(
                    db,
                    background_tasks,
                    user_id=updated_order.student_id,
                )
        return OrderResponse.model_validate(updated_order)
