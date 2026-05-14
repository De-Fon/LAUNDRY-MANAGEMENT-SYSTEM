"""Align payment schema with orders and idempotency.

Revision ID: 0001_audit_schema_alignment
Revises:
Create Date: 2026-05-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0001_audit_schema_alignment"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE order_status ADD VALUE IF NOT EXISTS 'CANCELLED'")

    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_constraint("uq_payments_provider_reference", type_="unique")
        batch_op.alter_column("booking_id", new_column_name="order_id", existing_type=sa.Integer())
        batch_op.alter_column("customer_id", new_column_name="student_id", existing_type=sa.Integer())
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=255), nullable=False))
        batch_op.create_unique_constraint("uq_payments_provider_reference", ["provider_reference"])
        batch_op.create_unique_constraint("uq_payments_idempotency_key", ["idempotency_key"])
        batch_op.create_foreign_key("fk_payments_order_id_orders", "orders", ["order_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_constraint("fk_payments_order_id_orders", type_="foreignkey")
        batch_op.drop_constraint("uq_payments_idempotency_key", type_="unique")
        batch_op.drop_constraint("uq_payments_provider_reference", type_="unique")
        batch_op.drop_column("idempotency_key")
        batch_op.alter_column("student_id", new_column_name="customer_id", existing_type=sa.Integer())
        batch_op.alter_column("order_id", new_column_name="booking_id", existing_type=sa.Integer())
        batch_op.create_unique_constraint("uq_payments_provider_reference", ["provider_reference"])
