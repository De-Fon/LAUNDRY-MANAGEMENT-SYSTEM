from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.apps.ledger.models import LedgerAccount, LedgerAuditLog, LedgerTransaction, TransactionStatus


class LedgerRepository:
    def create_ledger_account(self, db: Session, account: LedgerAccount) -> LedgerAccount:
        db.add(account)
        db.commit()
        db.refresh(account)
        return account

    def get_account_by_student(self, db: Session, student_id: int) -> LedgerAccount | None:
        statement = (
            select(LedgerAccount)
            .options(joinedload(LedgerAccount.transactions))
            .where(LedgerAccount.student_id == student_id)
        )
        return db.scalars(statement).unique().first()

    def get_account_by_id(self, db: Session, account_id: int) -> LedgerAccount | None:
        statement = (
            select(LedgerAccount)
            .options(joinedload(LedgerAccount.transactions))
            .where(LedgerAccount.id == account_id)
        )
        return db.scalars(statement).unique().first()

    def get_account_by_id_for_update(self, db: Session, account_id: int) -> LedgerAccount | None:
        statement = (
            select(LedgerAccount)
            .options(joinedload(LedgerAccount.transactions))
            .where(LedgerAccount.id == account_id)
            .with_for_update()
        )
        return db.scalars(statement).unique().first()

    def get_account_by_student_and_vendor(
        self,
        db: Session,
        student_id: int,
        vendor_id: int,
    ) -> LedgerAccount | None:
        statement = (
            select(LedgerAccount)
            .options(joinedload(LedgerAccount.transactions))
            .where(LedgerAccount.student_id == student_id, LedgerAccount.vendor_id == vendor_id)
        )
        return db.scalars(statement).unique().first()

    def update_account_balances(
        self,
        db: Session,
        account_id: int,
        total_billed: float,
        total_paid: float,
        total_outstanding: float,
        total_refunded: float,
    ) -> LedgerAccount | None:
        account = self.get_account_by_id(db, account_id)
        if account is None:
            return None

        account.total_billed = total_billed
        account.total_paid = total_paid
        account.total_outstanding = total_outstanding
        account.total_refunded = total_refunded
        db.commit()
        db.refresh(account)
        return account

    def create_transaction(self, db: Session, transaction: LedgerTransaction) -> LedgerTransaction:
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction

    def get_transaction_by_reference(self, db: Session, reference_code: str) -> LedgerTransaction | None:
        statement = (
            select(LedgerTransaction)
            .options(joinedload(LedgerTransaction.ledger_account), joinedload(LedgerTransaction.order))
            .where(LedgerTransaction.reference_code == reference_code)
        )
        return db.scalar(statement)

    def get_transactions_by_account(self, db: Session, account_id: int) -> list[LedgerTransaction]:
        statement = (
            select(LedgerTransaction)
            .options(joinedload(LedgerTransaction.ledger_account), joinedload(LedgerTransaction.order))
            .where(LedgerTransaction.ledger_account_id == account_id)
            .order_by(LedgerTransaction.created_at.desc())
        )
        return list(db.scalars(statement).all())

    def update_transaction_status(
        self,
        db: Session,
        transaction_id: int,
        status: TransactionStatus,
    ) -> LedgerTransaction | None:
        statement = (
            select(LedgerTransaction)
            .options(joinedload(LedgerTransaction.ledger_account), joinedload(LedgerTransaction.order))
            .where(LedgerTransaction.id == transaction_id)
        )
        transaction = db.scalar(statement)
        if transaction is None:
            return None

        transaction.transaction_status = status
        db.commit()
        db.refresh(transaction)
        return transaction

    def create_audit_log(self, db: Session, log: LedgerAuditLog) -> LedgerAuditLog:
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    def get_audit_logs_by_account(self, db: Session, account_id: int) -> list[LedgerAuditLog]:
        statement = (
            select(LedgerAuditLog)
            .options(joinedload(LedgerAuditLog.ledger_account), joinedload(LedgerAuditLog.transaction))
            .where(LedgerAuditLog.ledger_account_id == account_id)
            .order_by(LedgerAuditLog.created_at.asc())
        )
        return list(db.scalars(statement).all())

    def apply_transaction(
        self,
        db: Session,
        account: LedgerAccount,
        transaction: LedgerTransaction,
        audit_log: LedgerAuditLog,
        balances: tuple[float, float, float, float],
    ) -> LedgerTransaction:
        account.total_billed, account.total_paid, account.total_outstanding, account.total_refunded = balances
        transaction.transaction_status = TransactionStatus.COMPLETED
        db.add(transaction)
        db.flush()
        audit_log.transaction_id = transaction.id
        db.add(audit_log)
        db.commit()
        db.refresh(transaction)
        db.refresh(account)
        return transaction

    def reverse_transaction(
        self,
        db: Session,
        account: LedgerAccount,
        transaction: LedgerTransaction,
        audit_log: LedgerAuditLog,
        balances: tuple[float, float, float, float],
    ) -> LedgerTransaction:
        account.total_billed, account.total_paid, account.total_outstanding, account.total_refunded = balances
        transaction.transaction_status = TransactionStatus.REVERSED
        db.add(audit_log)
        db.commit()
        db.refresh(transaction)
        db.refresh(account)
        return transaction
