"""add listing_embedding table and pgvector extension

Revision ID: 004
Revises: 003
Create Date: 2026-05-03

"""

from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    is_postgres = op.get_bind().dialect.name == "postgresql"

    # `pgvector` extension and the `ivfflat` ANN index are Postgres-only.
    # SQLite tests still need the table itself to create cleanly.
    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    embedding_column = sa.Column(
        "embedding",
        pgvector.sqlalchemy.Vector(EMBEDDING_DIM) if is_postgres else sa.LargeBinary(),
        nullable=False,
    )

    op.create_table(
        "listing_embedding",
        sa.Column(
            "listing_id",
            sa.Integer(),
            sa.ForeignKey("listing.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        embedding_column,
        sa.Column("text_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("embedded_at", sa.DateTime(), nullable=False),
    )

    if is_postgres:
        op.execute(
            "CREATE INDEX listing_embedding_ann_idx ON listing_embedding "
            "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
        )


def downgrade() -> None:
    is_postgres = op.get_bind().dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP INDEX IF EXISTS listing_embedding_ann_idx;")
    op.drop_table("listing_embedding")
    # The `vector` extension is intentionally NOT dropped — future tables may
    # still depend on it.
