from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.apps.order_management.models import Order, OrderStatus, OrderStatusLog


class OrderRepository:
    def create_order(self, db: Session, order: Order) -> Order:
        db.add(order)
        db.commit()
        db.refresh(order)
        return order

    def get_order_by_id(self, db: Session, order_id: int) -> Order | None:
        statement = (
            select(Order)
            .options(
                joinedload(Order.service_item),
                selectinload(Order.status_history),
            )
            .where(Order.id == order_id)
        )
        return db.scalar(statement)

    def get_order_by_id_for_update(self, db: Session, order_id: int) -> Order | None:
        statement = (
            select(Order)
            .options(joinedload(Order.service_item))
            .where(Order.id == order_id)
            .with_for_update()
        )
        return db.scalar(statement)

    def get_order_by_code(self, db: Session, order_code: str) -> Order | None:
        statement = (
            select(Order)
            .options(
                joinedload(Order.service_item),
                selectinload(Order.status_history),
            )
            .where(Order.order_code == order_code)
        )
        return db.scalar(statement)

    def get_orders_by_student(self, db: Session, student_id: int) -> list[Order]:
        statement = select(Order).where(Order.student_id == student_id).order_by(Order.created_at.desc())
        return list(db.scalars(statement).all())

    def get_orders_by_vendor(self, db: Session, vendor_id: int) -> list[Order]:
        statement = select(Order).where(Order.vendor_id == vendor_id).order_by(Order.created_at.desc())
        return list(db.scalars(statement).all())

    def update_order_status(self, db: Session, order_id: int, new_status: OrderStatus) -> Order | None:
        order = self.get_order_by_id(db, order_id)
        if order is None:
            return None

        order.status = new_status
        db.commit()
        db.refresh(order)
        return order

    def apply_status_transition(
        self,
        db: Session,
        order: Order,
        new_status: OrderStatus,
        log: OrderStatusLog,
    ) -> Order:
        order.status = new_status
        db.add(log)
        db.commit()
        db.refresh(order)
        return order

    def create_status_log(self, db: Session, log: OrderStatusLog) -> OrderStatusLog:
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def get_status_logs(self, db: Session, order_id: int) -> list[OrderStatusLog]:
        statement = (
            select(OrderStatusLog)
            .where(OrderStatusLog.order_id == order_id)
            .order_by(OrderStatusLog.changed_at.asc())
        )
        return list(db.scalars(statement).all())
