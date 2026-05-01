"""add handover workflow

Revision ID: 20260501_000003
Revises: 20260424_000002
Create Date: 2026-05-01 00:00:03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260501_000003"
down_revision: Union[str, Sequence[str], None] = "20260424_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("items", "status", existing_type=sa.String(length=20), type_=sa.String(length=40), existing_nullable=False)
    op.alter_column("claims", "status", existing_type=sa.String(length=20), type_=sa.String(length=40), existing_nullable=False)
    op.add_column("claims", sa.Column("handover_note", sa.Text(), nullable=True))
    op.add_column("claims", sa.Column("handover_arranged_at", sa.DateTime(), nullable=True))
    op.add_column("claims", sa.Column("handed_over_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("claims", "handed_over_at")
    op.drop_column("claims", "handover_arranged_at")
    op.drop_column("claims", "handover_note")
    op.alter_column("claims", "status", existing_type=sa.String(length=40), type_=sa.String(length=20), existing_nullable=False)
    op.alter_column("items", "status", existing_type=sa.String(length=40), type_=sa.String(length=20), existing_nullable=False)
