"""Add Daraja payment lifecycle tables.

Revision ID: 20260516_0002
Revises: 20260513_0001
Create Date: 2026-05-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0002"
down_revision: str | None = "20260513_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'success'")
        op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'cancelled'")
        op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'timeout'")
        op.execute("ALTER TYPE paymentstatus ADD VALUE IF NOT EXISTS 'reversed'")

    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("phone_number", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("account_reference", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("checkout_request_id", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("merchant_request_id", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("provider_result_code", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("provider_result_description", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("last_queried_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("next_reconciliation_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint("uq_payments_checkout_request_id", ["checkout_request_id"])
        batch_op.create_index("ix_payments_checkout_request_id", ["checkout_request_id"])
        batch_op.create_index("ix_payments_merchant_request_id", ["merchant_request_id"])
        batch_op.create_index("ix_payments_next_reconciliation_at", ["next_reconciliation_at"])
        batch_op.create_index("ix_payments_student_status", ["student_id", "status"])

    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("started", "accepted", "rejected", "query_success", "query_failed", name="paymentattemptstatus"), nullable=False),
        sa.Column("checkout_request_id", sa.String(length=100), nullable=True),
        sa.Column("merchant_request_id", sa.String(length=100), nullable=True),
        sa.Column("request_payload", sa.JSON(), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checkout_request_id", name="uq_payment_attempts_checkout_request_id"),
    )
    op.create_index(op.f("ix_payment_attempts_id"), "payment_attempts", ["id"], unique=False)
    op.create_index(op.f("ix_payment_attempts_payment_id"), "payment_attempts", ["payment_id"], unique=False)
    op.create_index(op.f("ix_payment_attempts_checkout_request_id"), "payment_attempts", ["checkout_request_id"], unique=False)
    op.create_index(op.f("ix_payment_attempts_merchant_request_id"), "payment_attempts", ["merchant_request_id"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.Enum("stk_push", "stk_query", "callback", "reversal", name="transactiontype"), nullable=False),
        sa.Column("provider_transaction_id", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_transaction_id", name="uq_transactions_provider_transaction_id"),
    )
    op.create_index(op.f("ix_transactions_id"), "transactions", ["id"], unique=False)
    op.create_index(op.f("ix_transactions_payment_id"), "transactions", ["payment_id"], unique=False)
    op.create_index("ix_transactions_payment_type", "transactions", ["payment_id", "transaction_type"], unique=False)

    op.create_table(
        "callback_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("checkout_request_id", sa.String(length=100), nullable=True),
        sa.Column("merchant_request_id", sa.String(length=100), nullable=True),
        sa.Column("result_code", sa.Integer(), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payload_hash", name="uq_callback_logs_payload_hash"),
    )
    op.create_index(op.f("ix_callback_logs_id"), "callback_logs", ["id"], unique=False)
    op.create_index(op.f("ix_callback_logs_checkout_request_id"), "callback_logs", ["checkout_request_id"], unique=False)
    op.create_index(op.f("ix_callback_logs_merchant_request_id"), "callback_logs", ["merchant_request_id"], unique=False)
    op.create_index("ix_callback_logs_checkout_processed", "callback_logs", ["checkout_request_id", "processed"], unique=False)

    op.create_table(
        "payment_status_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.Enum("pending", "processing", "success", "failed", "cancelled", "timeout", "reversed", name="paymentstatus"), nullable=True),
        sa.Column("to_status", sa.Enum("pending", "processing", "success", "failed", "cancelled", "timeout", "reversed", name="paymentstatus"), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("changed_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payment_status_history_id"), "payment_status_history", ["id"], unique=False)
    op.create_index(op.f("ix_payment_status_history_payment_id"), "payment_status_history", ["payment_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payment_status_history_payment_id"), table_name="payment_status_history")
    op.drop_index(op.f("ix_payment_status_history_id"), table_name="payment_status_history")
    op.drop_table("payment_status_history")

    op.drop_index("ix_callback_logs_checkout_processed", table_name="callback_logs")
    op.drop_index(op.f("ix_callback_logs_merchant_request_id"), table_name="callback_logs")
    op.drop_index(op.f("ix_callback_logs_checkout_request_id"), table_name="callback_logs")
    op.drop_index(op.f("ix_callback_logs_id"), table_name="callback_logs")
    op.drop_table("callback_logs")

    op.drop_index("ix_transactions_payment_type", table_name="transactions")
    op.drop_index(op.f("ix_transactions_payment_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_id"), table_name="transactions")
    op.drop_table("transactions")

    op.drop_index(op.f("ix_payment_attempts_merchant_request_id"), table_name="payment_attempts")
    op.drop_index(op.f("ix_payment_attempts_checkout_request_id"), table_name="payment_attempts")
    op.drop_index(op.f("ix_payment_attempts_payment_id"), table_name="payment_attempts")
    op.drop_index(op.f("ix_payment_attempts_id"), table_name="payment_attempts")
    op.drop_table("payment_attempts")

    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_index("ix_payments_student_status")
        batch_op.drop_index("ix_payments_next_reconciliation_at")
        batch_op.drop_index("ix_payments_merchant_request_id")
        batch_op.drop_index("ix_payments_checkout_request_id")
        batch_op.drop_constraint("uq_payments_checkout_request_id", type_="unique")
        batch_op.drop_column("next_reconciliation_at")
        batch_op.drop_column("last_queried_at")
        batch_op.drop_column("retry_count")
        batch_op.drop_column("provider_result_description")
        batch_op.drop_column("provider_result_code")
        batch_op.drop_column("merchant_request_id")
        batch_op.drop_column("checkout_request_id")
        batch_op.drop_column("account_reference")
        batch_op.drop_column("phone_number")
