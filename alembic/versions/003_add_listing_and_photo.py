"""add listing and photo tables

Revision ID: 003
Revises: 002
Create Date: 2026-05-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "listing",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("era", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("manufacturer", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("condition", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["seller_id"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_listing_seller_id", "listing", ["seller_id"])

    op.create_table(
        "photo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("gcs_key", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("thumb_key", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["listing.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_photo_listing_id_sort_order",
        "photo",
        ["listing_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_photo_listing_id_sort_order", table_name="photo")
    op.drop_table("photo")
    op.drop_index("ix_listing_seller_id", table_name="listing")
    op.drop_table("listing")
