"""expand realistic schema

Revision ID: 20260424_000002
Revises: 20260403_000001
Create Date: 2026-04-24 00:00:02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260424_000002"
down_revision: Union[str, Sequence[str], None] = "20260403_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'MEMBER' WHERE role IN ('OWNER', 'FINDER')")

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("department", sa.String(length=120), nullable=True),
        sa.Column("preferred_contact_method", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.add_column("items", sa.Column("description_private", sa.Text(), nullable=True))
    op.add_column("items", sa.Column("brand", sa.String(length=120), nullable=True))
    op.add_column("items", sa.Column("color", sa.String(length=80), nullable=True))
    op.add_column("items", sa.Column("contact_preference", sa.String(length=50), nullable=True))
    op.add_column("items", sa.Column("resolved_at", sa.DateTime(), nullable=True))

    op.add_column("claims", sa.Column("proof_statement", sa.Text(), nullable=True))
    op.add_column("claims", sa.Column("decision_reason", sa.Text(), nullable=True))
    op.add_column("claims", sa.Column("decided_at", sa.DateTime(), nullable=True))

    op.create_table(
        "item_images",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_images_item_id"), "item_images", ["item_id"], unique=False)

    op.create_table(
        "item_timeline_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_timeline_events_item_id"), "item_timeline_events", ["item_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("related_item_id", sa.String(length=36), nullable=True),
        sa.Column("related_claim_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_item_timeline_events_item_id"), table_name="item_timeline_events")
    op.drop_table("item_timeline_events")
    op.drop_index(op.f("ix_item_images_item_id"), table_name="item_images")
    op.drop_table("item_images")

    op.drop_column("claims", "decided_at")
    op.drop_column("claims", "decision_reason")
    op.drop_column("claims", "proof_statement")

    op.drop_column("items", "resolved_at")
    op.drop_column("items", "contact_preference")
    op.drop_column("items", "color")
    op.drop_column("items", "brand")
    op.drop_column("items", "description_private")

    op.drop_table("user_profiles")
