from fastapi import HTTPException, status
from sqlalchemy.orm import Session

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
    def __init__(self, repository: LedgerRepository) -> None:
        self.repository = repository

    def open_ledger_account(self, db: Session, data: LedgerAccountCreate) -> LedgerAccountResponse:
        if self.repository.get_account_by_student_and_vendor(db, data.student_id, data.vendor_id) is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ledger account already exists")

        account = self.repository.create_ledger_account(
            db,
            LedgerAccount(student_id=data.student_id, vendor_id=data.vendor_id),
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
        account = self._get_account_or_404(db, data.ledger_account_id)
        self._ensure_vendor_owns_account(account, performed_by)

        balances = self._apply_balance_effect(account, data.transaction_type, data.amount)
        transaction = LedgerTransaction(
            ledger_account_id=data.ledger_account_id,
            order_id=data.order_id,
            transaction_type=data.transaction_type,
            transaction_status=TransactionStatus.PENDING,
            amount=self._money(data.amount),
            reference_code=self._generate_reference_code(db),
            description=data.description,
            performed_by=performed_by,
        )
        audit_log = LedgerAuditLog(
            ledger_account_id=account.id,
            previous_balance=account.total_outstanding,
            new_balance=balances[2],
            action="TRANSACTION",
            performed_by=performed_by,
            note=data.description,
        )
        saved = self.repository.apply_transaction(db, account, transaction, audit_log, balances)
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

        balances = self._reverse_balance_effect(account, transaction)
        audit_log = LedgerAuditLog(
            ledger_account_id=account.id,
            transaction_id=transaction.id,
            previous_balance=account.total_outstanding,
            new_balance=balances[2],
            action="REVERSAL",
            performed_by=performed_by,
            note=reason,
        )
        reversed_transaction = self.repository.reverse_transaction(db, account, transaction, audit_log, balances)
        return LedgerTransactionResponse.model_validate(reversed_transaction)

    def apply_adjustment(self, db: Session, data: LedgerAdjustmentCreate) -> LedgerTransactionResponse:
        if data.transaction_type not in {TransactionType.ADJUSTMENT, TransactionType.CREDIT, TransactionType.DEBIT}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid adjustment transaction type")

        return self.record_transaction(db, LedgerTransactionCreate(
            ledger_account_id=data.ledger_account_id,
            order_id=data.order_id,
            transaction_type=data.transaction_type,
            amount=data.amount,
            description=data.reason,
            idempotency_key="",
        ), data.performed_by)

    def fetch_audit_logs(self, db: Session, account_id: int, vendor_id: int) -> list[LedgerAuditLogResponse]:
        account = self._get_account_by_id_or_404(db, account_id)
        self._ensure_vendor_owns_account(account, vendor_id)
        return [LedgerAuditLogResponse.model_validate(log) for log in self.repository.get_audit_logs_by_account(db, account_id)]

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

        if transaction_type in {TransactionType.PAYMENT, TransactionType.CREDIT}:
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

        if transaction.transaction_type in {TransactionType.PAYMENT, TransactionType.CREDIT}:
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
        if balances[2] < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outstanding balance cannot be negative")
        return balances

    def _balances(self, account: LedgerAccount) -> tuple[float, float, float, float]:
        return account.total_billed, account.total_paid, account.total_outstanding, account.total_refunded

    def _generate_reference_code(self, db: Session) -> str:
        return f"TXN-{uuid4().hex[:10].upper()}"

    def _money(self, value: float) -> float:
        return round(value, 2)
