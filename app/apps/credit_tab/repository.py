from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.apps.credit_tab.models import CreditPayment, CreditStatus, CreditTab


class CreditRepository:
    def create_credit_tab(self, db: Session, tab: CreditTab) -> CreditTab:
        db.add(tab)
        db.commit()
        db.refresh(tab)
        return tab

    def get_tab_by_id(self, db: Session, tab_id: int) -> CreditTab | None:
        statement = (
            select(CreditTab)
            .options(
                joinedload(CreditTab.order),
                selectinload(CreditTab.payments),
            )
            .where(CreditTab.id == tab_id)
        )
        return db.scalar(statement)

    def get_tab_by_id_for_update(self, db: Session, tab_id: int) -> CreditTab | None:
        statement = select(CreditTab).where(CreditTab.id == tab_id).with_for_update()
        return db.scalar(statement)

    def get_tab_by_order_id(self, db: Session, order_id: int) -> CreditTab | None:
        statement = select(CreditTab).where(CreditTab.order_id == order_id)
        return db.scalar(statement)

    def get_tabs_by_student(self, db: Session, student_id: int) -> list[CreditTab]:
        statement = select(CreditTab).where(CreditTab.student_id == student_id).order_by(CreditTab.created_at.desc())
        return list(db.scalars(statement).all())

    def get_tabs_by_vendor(self, db: Session, vendor_id: int) -> list[CreditTab]:
        statement = select(CreditTab).where(CreditTab.vendor_id == vendor_id).order_by(CreditTab.created_at.desc())
        return list(db.scalars(statement).all())

    def get_unpaid_tabs_by_student(self, db: Session, student_id: int) -> list[CreditTab]:
        statement = (
            select(CreditTab)
            .where(
                CreditTab.student_id == student_id,
                CreditTab.status.in_([CreditStatus.UNPAID, CreditStatus.PARTIAL]),
            )
            .order_by(CreditTab.created_at.desc())
        )
        return list(db.scalars(statement).all())

    def update_tab_balance(
        self,
        db: Session,
        tab_id: int,
        amount_paid: float,
        outstanding_balance: float,
        status: CreditStatus,
    ) -> CreditTab | None:
        tab = self.get_tab_by_id(db, tab_id)
        if tab is None:
            return None

        tab.amount_paid = amount_paid
        tab.outstanding_balance = outstanding_balance
        tab.status = status
        db.commit()
        db.refresh(tab)
        return tab

    def create_credit_payment(self, db: Session, payment: CreditPayment) -> CreditPayment:
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    def get_payment_by_idempotency_key(self, db: Session, key: str) -> CreditPayment | None:
        statement = select(CreditPayment).where(CreditPayment.idempotency_key == key)
        return db.scalar(statement)

    def get_payments_by_tab(self, db: Session, tab_id: int) -> list[CreditPayment]:
        statement = (
            select(CreditPayment)
            .where(CreditPayment.credit_tab_id == tab_id)
            .order_by(CreditPayment.paid_at.asc())
        )
        return list(db.scalars(statement).all())

    def apply_payment(
        self,
        db: Session,
        tab: CreditTab,
        payment: CreditPayment,
        amount_paid: float,
        outstanding_balance: float,
        status: CreditStatus,
    ) -> CreditPayment:
        tab.amount_paid = amount_paid
        tab.outstanding_balance = outstanding_balance
        tab.status = status
        db.add(payment)
        db.commit()
        db.refresh(payment)
        db.refresh(tab)
        return payment
