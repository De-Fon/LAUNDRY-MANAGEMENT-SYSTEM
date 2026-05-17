"""test_template

Revision ID: 2efa5c4d6c29
Revises: 0001
Create Date: 2026-05-17 12:48:59.844024
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '2efa5c4d6c29'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
