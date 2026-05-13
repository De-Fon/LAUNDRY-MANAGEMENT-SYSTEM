from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.apps.idempotency.schemas import IdempotencyKeySchema
from app.apps.ledger.models import TransactionStatus, TransactionType


class LedgerAccountCreate(BaseModel):
    student_id: int
    vendor_id: int


class LedgerTransactionCreate(IdempotencyKeySchema):
    ledger_account_id: int
    order_id: int | None = None
    transaction_type: TransactionType
    amount: float = Field(..., gt=0)
    description: str | None = None


class LedgerAdjustmentCreate(IdempotencyKeySchema):
    ledger_account_id: int
    amount: float = Field(..., gt=0)
    transaction_type: TransactionType
    reason: str
    performed_by: int


class LedgerReverseCreate(BaseModel):
    reference_code: str
    reason: str


class LedgerTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ledger_account_id: int
    order_id: int | None
    transaction_type: TransactionType
    transaction_status: TransactionStatus
    amount: float
    reference_code: str
    idempotency_key: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class LedgerAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    vendor_id: int
    total_billed: float
    total_paid: float
    total_outstanding: float
    total_refunded: float
    created_at: datetime
    updated_at: datetime


class LedgerAccountDetailResponse(LedgerAccountResponse):
    transactions: list[LedgerTransactionResponse]


class LedgerAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ledger_account_id: int
    transaction_id: int
    action: str
    performed_by: int
    previous_balance: float
    new_balance: float
    note: str | None
    created_at: datetime


class LedgerSummaryResponse(BaseModel):
    student_id: int
    vendor_id: int
    total_billed: float
    total_paid: float
    total_outstanding: float
    total_refunded: float
    transaction_count: int
    last_transaction_at: datetime | None
