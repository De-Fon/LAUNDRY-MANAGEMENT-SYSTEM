from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.catalog.repository import CatalogRepository
from app.apps.order_management.models import Order, OrderStatus, OrderStatusLog
from app.apps.order_management.repository import OrderRepository
from app.apps.order_management.schemas import (
    OrderCreate,
    OrderDetailResponse,
    OrderResponse,
    OrderStatusLogResponse,
    OrderStatusUpdate,
)
from app.apps.pricing.repository import PricingRepository
from app.apps.pricing.service import calculate_final_price


VALID_TRANSITIONS = {
    OrderStatus.QUEUED: OrderStatus.WASHING,
    OrderStatus.WASHING: OrderStatus.DRYING,
    OrderStatus.DRYING: OrderStatus.READY,
    OrderStatus.READY: OrderStatus.WAITING_TO_PICK,
    OrderStatus.WAITING_TO_PICK: OrderStatus.PICKED_UP,
}


class OrderService:
    def __init__(
        self,
        order_repository: OrderRepository,
        catalog_repository: CatalogRepository,
        pricing_repository: PricingRepository,
    ) -> None:
        self.order_repository = order_repository
        self.catalog_repository = catalog_repository
        self.pricing_repository = pricing_repository

    def place_order(self, db: Session, student_id: int, data: OrderCreate) -> OrderResponse:
        total_price = self._calculate_total_price(db, data)
        order = self.order_repository.create_order(
            db,
            Order(
                order_code=self._generate_order_code(),
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

        return self._build_order_detail(order, self.order_repository.get_status_logs(db, order.id))

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
    ) -> OrderResponse:
        order = self._get_order_for_update_or_404(db, order_id)
        self._ensure_vendor_owns_order(order, changed_by)
        self._ensure_valid_transition(order.status, status_update.status)

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
        return OrderResponse.model_validate(updated_order)

    def _calculate_total_price(self, db: Session, data: OrderCreate) -> float:
        service_item = self.catalog_repository.get_item_by_id(db, data.service_item_id)
        if service_item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service item not found")

        wash_type = self.pricing_repository.get_wash_type_by_name(db, data.wash_type)
        if wash_type is None or not wash_type.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wash type not found")

        item_price = calculate_final_price(service_item.base_price, wash_type.price_multiplier)
        return round(item_price * data.quantity, 2)

    def _generate_order_code(self) -> str:
        return f"ORD-{uuid4().hex[:8].upper()}"

    def _get_order_for_update_or_404(self, db: Session, order_id: int) -> Order:
        order = self.order_repository.get_order_by_id_for_update(db, order_id)
        if order is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    def _ensure_vendor_owns_order(self, order: Order, vendor_id: int) -> None:
        if order.vendor_id != vendor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own orders")

    def _ensure_valid_transition(self, previous_status: OrderStatus, new_status: OrderStatus) -> None:
        if VALID_TRANSITIONS.get(previous_status) != new_status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status transition")

    def _build_order_detail(self, order: Order, status_history: list[OrderStatusLog]) -> OrderDetailResponse:
        return OrderDetailResponse(
            **OrderResponse.model_validate(order).model_dump(),
            status_history=[OrderStatusLogResponse.model_validate(log) for log in status_history],
        )
