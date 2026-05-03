"""ListingEmbedding model.

One row per Listing, holding a fixed-dimension vector embedding of the
listing's title + description. Powers the natural-language search
feature (the product's differentiator). The pgvector extension and the
ANN index are Postgres-only and are created by the Alembic migration
under a dialect guard; the model itself is loadable in SQLite tests.
"""

from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, SQLModel

EMBEDDING_DIM = 1024


class ListingEmbedding(SQLModel, table=True):
    __tablename__ = "listing_embedding"

    listing_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("listing.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )
    embedding: list[float] = Field(
        sa_column=Column(Vector(EMBEDDING_DIM), nullable=False),
    )
    text_hash: str = Field(max_length=64)
    embedded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
