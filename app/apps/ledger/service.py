from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app.apps.idempotency.service import IdempotencyService
from app.apps.ledger.models import LedgerAccount, LedgerAuditLog, LedgerTransaction, TransactionStatus, TransactionType
from app.apps.ledger.repository import LedgerRepository
from app.apps.ledger.schemas import (
    LedgerAccountCreate,
    LedgerAccountDetailResponse,
    LedgerAccountResponse,
    LedgerAdjustmentCreate,
    LedgerAuditLogResponse,
    LedgerSummaryResponse,
    LedgerTransactionCreate,
    LedgerTransactionResponse,
)


class LedgerService:
    def __init__(
        self,
        repository: LedgerRepository,
        idempotency_service: IdempotencyService,
    ) -> None:
        self.repository = repository
        self.idempotency_service = idempotency_service

    def open_ledger_account(self, db: Session, data: LedgerAccountCreate) -> LedgerAccountResponse:
        if self.repository.get_account_by_student_and_vendor(db, data.student_id, data.vendor_id) is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ledger account already exists")

        account = self.repository.create_ledger_account(
            db,
            LedgerAccount(student_id=data.student_id, vendor_id=data.vendor_id),
        )
        logger.info(
            "LEDGER ACCOUNT OPENED | account={} student={} vendor={} timestamp={}",
            account.id,
            account.student_id,
            account.vendor_id,
            self._timestamp(),
        )
        return LedgerAccountResponse.model_validate(account)

    def fetch_account(self, db: Session, student_id: int, vendor_id: int | None = None) -> LedgerAccountDetailResponse:
        account = self._get_account_for_student(db, student_id, vendor_id)
        transactions = self.repository.get_transactions_by_account(db, account.id)
        return LedgerAccountDetailResponse(
            **LedgerAccountResponse.model_validate(account).model_dump(),
            transactions=[LedgerTransactionResponse.model_validate(transaction) for transaction in transactions],
        )

    def fetch_account_summary(self, db: Session, student_id: int, vendor_id: int | None = None) -> LedgerSummaryResponse:
        account = self._get_account_for_student(db, student_id, vendor_id)
        transactions = self.repository.get_transactions_by_account(db, account.id)
        return LedgerSummaryResponse(
            student_id=account.student_id,
            vendor_id=account.vendor_id,
            total_billed=account.total_billed,
            total_paid=account.total_paid,
            total_outstanding=account.total_outstanding,
            total_refunded=account.total_refunded,
            transaction_count=len(transactions),
            last_transaction_at=transactions[0].created_at if transactions else None,
        )

    def record_transaction(
        self,
        db: Session,
        data: LedgerTransactionCreate,
        performed_by: int,
    ) -> LedgerTransactionResponse:
        if transaction := self.idempotency_service.find_duplicate(db, LedgerTransaction, data.idempotency_key):
            self.idempotency_service.log_duplicate(data.idempotency_key, "TRANSACTION", transaction.ledger_account_id)
            return LedgerTransactionResponse.model_validate(transaction)

        account = self._get_account_or_404(db, data.ledger_account_id)
        self._ensure_vendor_owns_account(account, performed_by)

        previous_balance = account.total_outstanding
        balances = self._apply_balance_effect(account, data.transaction_type, data.amount)
        transaction = LedgerTransaction(
            ledger_account_id=account.id,
            order_id=data.order_id,
            transaction_type=data.transaction_type,
            transaction_status=TransactionStatus.PENDING,
            amount=self._money(data.amount),
            reference_code=self._generate_reference_code(db),
            idempotency_key=data.idempotency_key,
            description=data.description,
        )
        saved = self.repository.apply_transaction(
            db,
            account,
            transaction,
            self._audit_log(account.id, 0, "TRANSACTION", performed_by, previous_balance, balances[2], data.description),
            balances,
        )
        self._log_transaction(saved, balances[2], performed_by)
        return LedgerTransactionResponse.model_validate(saved)

    def reverse_transaction(
        self,
        db: Session,
        reference_code: str,
        performed_by: int,
        reason: str,
    ) -> LedgerTransactionResponse:
        transaction = self.repository.get_transaction_by_reference(db, reference_code)
        if transaction is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger transaction not found")
        if transaction.transaction_status != TransactionStatus.COMPLETED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaction cannot be reversed")

        account = self._get_account_or_404(db, transaction.ledger_account_id)
        self._ensure_vendor_owns_account(account, performed_by)

        previous_balance = account.total_outstanding
        balances = self._reverse_balance_effect(account, transaction)
        reversed_transaction = self.repository.reverse_transaction(
            db,
            account,
            transaction,
            self._audit_log(account.id, transaction.id, "REVERSAL", performed_by, previous_balance, balances[2], reason),
            balances,
        )
        logger.warning(
            "TRANSACTION REVERSED | ref={} amount=KES {} reason={} performed_by={} timestamp={}",
            reference_code,
            transaction.amount,
            reason,
            performed_by,
            self._timestamp(),
        )
        return LedgerTransactionResponse.model_validate(reversed_transaction)

    def apply_adjustment(self, db: Session, data: LedgerAdjustmentCreate) -> LedgerTransactionResponse:
        if data.transaction_type not in {TransactionType.ADJUSTMENT, TransactionType.CREDIT, TransactionType.DEBIT}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid adjustment transaction type")

        response = self.record_transaction(
            db,
            LedgerTransactionCreate(
                ledger_account_id=data.ledger_account_id,
                transaction_type=data.transaction_type,
                amount=data.amount,
                idempotency_key=data.idempotency_key,
                description=data.reason,
            ),
            data.performed_by,
        )
        logger.info(
            "ADJUSTMENT APPLIED | account={} amount=KES {} type={} reason={} timestamp={}",
            data.ledger_account_id,
            data.amount,
            data.transaction_type.value,
            data.reason,
            self._timestamp(),
        )
        return response

    def fetch_audit_logs(self, db: Session, account_id: int, vendor_id: int) -> list[LedgerAuditLogResponse]:
        account = self._get_account_by_id_or_404(db, account_id)
        self._ensure_vendor_owns_account(account, vendor_id)
        return [
            LedgerAuditLogResponse.model_validate(log)
            for log in self.repository.get_audit_logs_by_account(db, account_id)
        ]

    def _get_account_for_student(self, db: Session, student_id: int, vendor_id: int | None) -> LedgerAccount:
        account = (
            self.repository.get_account_by_student_and_vendor(db, student_id, vendor_id)
            if vendor_id is not None
            else self.repository.get_account_by_student(db, student_id)
        )
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger account not found")
        return account

    def _get_account_or_404(self, db: Session, account_id: int) -> LedgerAccount:
        account = self.repository.get_account_by_id_for_update(db, account_id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger account not found")
        return account

    def _get_account_by_id_or_404(self, db: Session, account_id: int) -> LedgerAccount:
        account = self.repository.get_account_by_id(db, account_id)
        if account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ledger account not found")
        return account

    def _ensure_vendor_owns_account(self, account: LedgerAccount, vendor_id: int) -> None:
        if account.vendor_id != vendor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage your own ledgers")

    def _apply_balance_effect(
        self,
        account: LedgerAccount,
        transaction_type: TransactionType,
        amount: float,
    ) -> tuple[float, float, float, float]:
        billed, paid, outstanding, refunded = self._balances(account)
        amount = self._money(amount)

        if transaction_type == TransactionType.PAYMENT:
            paid += amount
            outstanding -= amount
        elif transaction_type == TransactionType.CREDIT:
            paid += amount
            outstanding -= amount
        elif transaction_type == TransactionType.DEBIT:
            billed += amount
            outstanding += amount
        elif transaction_type == TransactionType.REFUND:
            refunded += amount
            outstanding += amount
        elif transaction_type == TransactionType.ADJUSTMENT:
            billed += amount
            outstanding += amount

        return self._validate_balances(billed, paid, outstanding, refunded)

    def _reverse_balance_effect(
        self,
        account: LedgerAccount,
        transaction: LedgerTransaction,
    ) -> tuple[float, float, float, float]:
        billed, paid, outstanding, refunded = self._balances(account)
        amount = transaction.amount

        if transaction.transaction_type == TransactionType.PAYMENT:
            paid -= amount
            outstanding += amount
        elif transaction.transaction_type == TransactionType.CREDIT:
            paid -= amount
            outstanding += amount
        elif transaction.transaction_type == TransactionType.DEBIT:
            billed -= amount
            outstanding -= amount
        elif transaction.transaction_type == TransactionType.REFUND:
            refunded -= amount
            outstanding -= amount
        elif transaction.transaction_type == TransactionType.ADJUSTMENT:
            billed -= amount
            outstanding -= amount

        return self._validate_balances(billed, paid, outstanding, refunded)

    def _validate_balances(
        self,
        billed: float,
        paid: float,
        outstanding: float,
        refunded: float,
    ) -> tuple[float, float, float, float]:
        balances = tuple(self._money(value) for value in (billed, paid, outstanding, refunded))
        if any(value < 0 for value in balances):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ledger balance cannot go below 0")
        return balances

    def _balances(self, account: LedgerAccount) -> tuple[float, float, float, float]:
        return account.total_billed, account.total_paid, account.total_outstanding, account.total_refunded

    def _audit_log(
        self,
        account_id: int,
        transaction_id: int,
        action: str,
        performed_by: int,
        previous_balance: float,
        new_balance: float,
        note: str | None,
    ) -> LedgerAuditLog:
        return LedgerAuditLog(
            ledger_account_id=account_id,
            transaction_id=transaction_id,
            action=action,
            performed_by=performed_by,
            previous_balance=previous_balance,
            new_balance=new_balance,
            note=note,
        )

    def _generate_reference_code(self, db: Session) -> str:
        while True:
            reference_code = f"TXN-{uuid4().hex[:8].upper()}"
            if self.repository.get_transaction_by_reference(db, reference_code) is None:
                return reference_code

    def _log_transaction(self, transaction: LedgerTransaction, outstanding: float, performed_by: int) -> None:
        logger.info(
            "TRANSACTION RECORDED | ref={} type={} amount=KES {} outstanding=KES {} performed_by={} timestamp={}",
            transaction.reference_code,
            transaction.transaction_type.value,
            transaction.amount,
            outstanding,
            performed_by,
            self._timestamp(),
        )

    def _money(self, value: float) -> float:
        return round(value, 2)

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()
