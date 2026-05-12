from datetime import UTC, datetime

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.apps.credit_tab.models import CreditPayment, CreditStatus, CreditTab
from app.apps.credit_tab.repository import CreditRepository
from app.apps.credit_tab.schemas import (
    CreditPaymentCreate,
    CreditPaymentResponse,
    CreditTabCreate,
    CreditTabDetailResponse,
    CreditTabResponse,
    DebtReminderSummary,
)


class CreditService:
    def __init__(self, repository: CreditRepository) -> None:
        self.repository = repository

    def open_credit_tab(self, db: Session, vendor_id: int, data: CreditTabCreate) -> CreditTabResponse:
        if data.vendor_id != vendor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only open your own credit tabs")
        if self.repository.get_tab_by_order_id(db, data.order_id) is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credit tab already exists for order")

        tab = self.repository.create_credit_tab(
            db,
            CreditTab(
                student_id=data.student_id,
                vendor_id=data.vendor_id,
                order_id=data.order_id,
                total_amount=data.total_amount,
                amount_paid=0.0,
                outstanding_balance=data.total_amount,
                status=CreditStatus.UNPAID,
                due_date=data.due_date,
            ),
        )
        self._log_tab_opened(tab)
        return CreditTabResponse.model_validate(tab)

    def fetch_tab(self, db: Session, tab_id: int, student_id: int) -> CreditTabDetailResponse:
        tab = self._get_tab_or_404(db, tab_id)
        if tab.student_id != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own tabs")

        return self._build_tab_detail(tab, self.repository.get_payments_by_tab(db, tab_id))

    def fetch_student_tabs(self, db: Session, student_id: int) -> list[CreditTabResponse]:
        return [CreditTabResponse.model_validate(tab) for tab in self.repository.get_tabs_by_student(db, student_id)]

    def fetch_vendor_tabs(self, db: Session, vendor_id: int) -> list[CreditTabResponse]:
        return [CreditTabResponse.model_validate(tab) for tab in self.repository.get_tabs_by_vendor(db, vendor_id)]

    def fetch_unpaid_tabs(self, db: Session, student_id: int) -> list[CreditTabResponse]:
        return [CreditTabResponse.model_validate(tab) for tab in self.repository.get_unpaid_tabs_by_student(db, student_id)]

    def record_payment(self, db: Session, vendor_id: int, data: CreditPaymentCreate) -> CreditPaymentResponse:
        if payment := self.repository.get_payment_by_idempotency_key(db, data.idempotency_key):
            self._log_duplicate_payment(data.idempotency_key, payment.credit_tab_id)
            return CreditPaymentResponse.model_validate(payment)

        tab = self._get_tab_for_payment(db, data.credit_tab_id, vendor_id)
        self._validate_payment_amount(tab, data.amount_paid)

        new_amount_paid = round(tab.amount_paid + data.amount_paid, 2)
        new_balance = round(tab.total_amount - new_amount_paid, 2)
        new_status = self._calculate_status(tab.total_amount, new_balance)
        payment = self.repository.apply_payment(
            db,
            tab,
            CreditPayment(
                credit_tab_id=data.credit_tab_id,
                amount_paid=data.amount_paid,
                payment_method=data.payment_method,
                idempotency_key=data.idempotency_key,
                note=data.note,
            ),
            new_amount_paid,
            new_balance,
            new_status,
        )
        self._log_payment_recorded(tab.id, data.amount_paid, data.payment_method, new_balance, new_status)
        return CreditPaymentResponse.model_validate(payment)

    def send_debt_reminder(self, db: Session, vendor_id: int, student_id: int) -> DebtReminderSummary:
        tabs = [
            tab
            for tab in self.repository.get_unpaid_tabs_by_student(db, student_id)
            if tab.vendor_id == vendor_id
        ]
        total_outstanding = round(sum(tab.outstanding_balance for tab in tabs), 2)
        self._log_reminder(student_id, len(tabs), total_outstanding)
        return DebtReminderSummary(total_tabs=len(tabs), total_outstanding=total_outstanding)

    def _get_tab_or_404(self, db: Session, tab_id: int) -> CreditTab:
        tab = self.repository.get_tab_by_id(db, tab_id)
        if tab is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit tab not found")
        return tab

    def _get_tab_for_payment(self, db: Session, tab_id: int, vendor_id: int) -> CreditTab:
        tab = self.repository.get_tab_by_id_for_update(db, tab_id)
        if tab is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credit tab not found")
        if tab.vendor_id != vendor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage your own tabs")
        if tab.status == CreditStatus.PAID or tab.outstanding_balance == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Credit tab is already paid")
        return tab

    def _validate_payment_amount(self, tab: CreditTab, amount: float) -> None:
        if amount <= tab.outstanding_balance:
            return

        logger.warning(
            "OVERPAYMENT ATTEMPT | tab={} tried=KES {} balance=KES {} timestamp={}",
            tab.id,
            amount,
            tab.outstanding_balance,
            self._timestamp(),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment exceeds outstanding balance")

    def _calculate_status(self, total_amount: float, outstanding_balance: float) -> CreditStatus:
        if outstanding_balance == 0:
            return CreditStatus.PAID
        if 0 < outstanding_balance < total_amount:
            return CreditStatus.PARTIAL
        return CreditStatus.UNPAID

    def _build_tab_detail(self, tab: CreditTab, payments: list[CreditPayment]) -> CreditTabDetailResponse:
        return CreditTabDetailResponse(
            **CreditTabResponse.model_validate(tab).model_dump(),
            payments=[CreditPaymentResponse.model_validate(payment) for payment in payments],
        )

    def _log_tab_opened(self, tab: CreditTab) -> None:
        logger.info(
            "CREDIT TAB OPENED | tab={} student={} order={} total=KES {} timestamp={}",
            tab.id,
            tab.student_id,
            tab.order_id,
            tab.total_amount,
            self._timestamp(),
        )

    def _log_payment_recorded(
        self,
        tab_id: int,
        amount_paid: float,
        payment_method: str,
        new_balance: float,
        new_status: CreditStatus,
    ) -> None:
        logger.info(
            "PAYMENT RECORDED | tab={} amount=KES {} method={} balance=KES {} status={} timestamp={}",
            tab_id,
            amount_paid,
            payment_method,
            new_balance,
            new_status.value,
            self._timestamp(),
        )

    def _log_duplicate_payment(self, key: str, tab_id: int) -> None:
        logger.warning("DUPLICATE PAYMENT BLOCKED | key={} tab={} timestamp={}", key, tab_id, self._timestamp())

    def _log_reminder(self, student_id: int, total_tabs: int, total_outstanding: float) -> None:
        logger.info(
            "REMINDER TRIGGERED | student={} total_tabs={} total_outstanding=KES {} timestamp={}",
            student_id,
            total_tabs,
            total_outstanding,
            self._timestamp(),
        )

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()
