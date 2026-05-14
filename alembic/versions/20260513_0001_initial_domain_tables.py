"""Add booking and notification tables.

Revision ID: 20260513_0001
Revises: 0001_audit_schema_alignment
Create Date: 2026-05-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260513_0001"
down_revision: str | None = "0001_audit_schema_alignment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "confirmed",
                "picked_up",
                "in_progress",
                "ready",
                "completed",
                "cancelled",
                name="bookingstatus",
            ),
            nullable=False,
        ),
        sa.Column("pickup_address", sa.String(length=500), nullable=False),
        sa.Column("delivery_address", sa.String(length=500), nullable=True),
        sa.Column("pickup_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bookings_customer_id"), "bookings", ["customer_id"], unique=False)
    op.create_index(op.f("ix_bookings_id"), "bookings", ["id"], unique=False)
    op.create_index(op.f("ix_bookings_vendor_id"), "bookings", ["vendor_id"], unique=False)

    op.create_table(
        "booking_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("service_item_id", sa.Integer(), nullable=False),
        sa.Column("wash_type_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("line_total", sa.Float(), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["service_item_id"], ["service_items.id"]),
        sa.ForeignKeyConstraint(["wash_type_id"], ["wash_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_booking_items_booking_id"), "booking_items", ["booking_id"], unique=False)
    op.create_index(op.f("ix_booking_items_id"), "booking_items", ["id"], unique=False)
    op.create_index(op.f("ix_booking_items_service_item_id"), "booking_items", ["service_item_id"], unique=False)
    op.create_index(op.f("ix_booking_items_wash_type_id"), "booking_items", ["wash_type_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.Enum("in_app", "sms", "email", name="notificationchannel"), nullable=False),
        sa.Column("status", sa.Enum("queued", "sent", "failed", "read", name="notificationstatus"), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_id"), table_name="notifications")
    op.drop_table("notifications")

    op.drop_index(op.f("ix_booking_items_wash_type_id"), table_name="booking_items")
    op.drop_index(op.f("ix_booking_items_service_item_id"), table_name="booking_items")
    op.drop_index(op.f("ix_booking_items_id"), table_name="booking_items")
    op.drop_index(op.f("ix_booking_items_booking_id"), table_name="booking_items")
    op.drop_table("booking_items")

    op.drop_index(op.f("ix_bookings_vendor_id"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_id"), table_name="bookings")
    op.drop_index(op.f("ix_bookings_customer_id"), table_name="bookings")
    op.drop_table("bookings")
