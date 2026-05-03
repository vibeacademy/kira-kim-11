"""Tests for the ListingEmbedding model.

Most assertions about vector behavior require a Postgres engine with
`pgvector` installed; those tests skip when the test session is using
SQLite (the conftest default). The smoke tests here verify that the
model imports and that the table creates cleanly even on SQLite.
"""

import pytest
from sqlalchemy.exc import DataError
from sqlmodel import Session

from app.models import EMBEDDING_DIM, Listing, ListingEmbedding, User


def _is_postgres(session: Session) -> bool:
    return session.get_bind().dialect.name == "postgresql"


def test_model_imports() -> None:
    """The class is importable and has the documented dimension constant."""
    assert ListingEmbedding is not None
    assert EMBEDDING_DIM == 1024


def test_table_creates_on_test_engine(session: Session) -> None:
    """The conftest fixture runs `metadata.create_all`. If this test gets a
    session at all, the table was created without erroring on the test
    engine (SQLite by default)."""
    assert "listing_embedding" in ListingEmbedding.metadata.tables


def test_persist_embedding_with_correct_dim(session: Session) -> None:
    """A 1024-dim vector roundtrips. Skipped on SQLite — pgvector's roundtrip
    logic is Postgres-specific."""
    if not _is_postgres(session):
        pytest.skip("pgvector roundtrip requires Postgres; default test engine is SQLite")

    seller = User(email="seller@example.com", password_hash="$2b$12$placeholder")
    session.add(seller)
    session.commit()
    session.refresh(seller)

    listing = Listing(seller_id=seller.id, title="Vintage Bear", description="A rare 1985 bear.")
    session.add(listing)
    session.commit()
    session.refresh(listing)

    embedding = [0.01] * EMBEDDING_DIM
    row = ListingEmbedding(listing_id=listing.id, embedding=embedding, text_hash="abc123")
    session.add(row)
    session.commit()

    fetched = session.get(ListingEmbedding, listing.id)
    assert fetched is not None
    assert len(fetched.embedding) == EMBEDDING_DIM


def test_reject_wrong_dim(session: Session) -> None:
    """Inserting a vector of the wrong dimension raises. Postgres-only."""
    if not _is_postgres(session):
        pytest.skip("pgvector dimension check requires Postgres")

    seller = User(email="seller2@example.com", password_hash="$2b$12$placeholder")
    session.add(seller)
    session.commit()
    session.refresh(seller)

    listing = Listing(seller_id=seller.id, title="Another Bear", description="Yet another.")
    session.add(listing)
    session.commit()
    session.refresh(listing)

    wrong_dim = [0.0] * (EMBEDDING_DIM - 1)
    row = ListingEmbedding(listing_id=listing.id, embedding=wrong_dim, text_hash="def456")
    session.add(row)
    with pytest.raises(DataError):
        session.commit()
