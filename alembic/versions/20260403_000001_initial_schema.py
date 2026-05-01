"""initial schema

Revision ID: 20260403_000001
Revises:
Create Date: 2026-04-03 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260403_000001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("report_type", sa.String(length=10), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description_public", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("location_text", sa.String(length=255), nullable=False),
        sa.Column("happened_at", sa.DateTime(), nullable=False),
        sa.Column("posted_by_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("active_claim_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_items_category"), "items", ["category"], unique=False)
    op.create_index(
        op.f("ix_items_posted_by_user_id"),
        "items",
        ["posted_by_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_items_status"), "items", ["status"], unique=False)

    op.create_table(
        "claims",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("claimant_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_claims_claimant_user_id"), "claims", ["claimant_user_id"], unique=False)
    op.create_index(op.f("ix_claims_item_id"), "claims", ["item_id"], unique=False)
    op.create_index(op.f("ix_claims_status"), "claims", ["status"], unique=False)

    op.create_table(
        "claim_answers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("claim_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_claim_answers_claim_id"), "claim_answers", ["claim_id"], unique=False)

    op.create_table(
        "verification_questions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_verification_questions_item_id"),
        "verification_questions",
        ["item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_verification_questions_item_id"), table_name="verification_questions")
    op.drop_table("verification_questions")
    op.drop_index(op.f("ix_claim_answers_claim_id"), table_name="claim_answers")
    op.drop_table("claim_answers")
    op.drop_index(op.f("ix_claims_status"), table_name="claims")
    op.drop_index(op.f("ix_claims_item_id"), table_name="claims")
    op.drop_index(op.f("ix_claims_claimant_user_id"), table_name="claims")
    op.drop_table("claims")
    op.drop_index(op.f("ix_items_status"), table_name="items")
    op.drop_index(op.f("ix_items_posted_by_user_id"), table_name="items")
    op.drop_index(op.f("ix_items_category"), table_name="items")
    op.drop_table("items")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
