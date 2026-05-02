"""Tests for the Listing and Photo models."""

import pytest
from sqlmodel import Session, select

from app.models import Listing, Photo, User


def test_user_listing_photos_chain_and_ordering(session: Session) -> None:
    seller = User(email="seller@example.com", password_hash="$2b$12$placeholder")
    session.add(seller)
    session.commit()
    session.refresh(seller)
    assert seller.id is not None

    listing = Listing(
        seller_id=seller.id,
        title="Vintage Beanie Baby",
        description="Patti the Platypus, 1993, mint condition",
        era="1990s",
        manufacturer="Ty",
        condition="mint",
    )
    session.add(listing)
    session.commit()
    session.refresh(listing)
    assert listing.id is not None

    # Insert photos out of sort_order on purpose to verify ordering.
    session.add(Photo(listing_id=listing.id, gcs_key="photos/1.jpg", sort_order=1))
    session.add(Photo(listing_id=listing.id, gcs_key="photos/0.jpg", sort_order=0))
    session.commit()

    found = session.exec(select(Listing).where(Listing.id == listing.id)).one()
    assert found.title == "Vintage Beanie Baby"
    assert found.status == "active"
    assert len(found.photos) == 2
    assert [p.sort_order for p in found.photos] == [0, 1]
    assert [p.gcs_key for p in found.photos] == ["photos/0.jpg", "photos/1.jpg"]


def test_deleting_listing_cascades_to_photos(session: Session) -> None:
    seller = User(email="seller2@example.com", password_hash="hash")
    session.add(seller)
    session.commit()
    session.refresh(seller)
    assert seller.id is not None

    listing = Listing(seller_id=seller.id, title="A bear", description="brown teddy")
    session.add(listing)
    session.commit()
    session.refresh(listing)
    assert listing.id is not None

    session.add(Photo(listing_id=listing.id, gcs_key="a.jpg"))
    session.add(Photo(listing_id=listing.id, gcs_key="b.jpg"))
    session.commit()

    listing_id = listing.id
    assert len(session.exec(select(Photo).where(Photo.listing_id == listing_id)).all()) == 2

    session.delete(listing)
    session.commit()

    assert session.exec(select(Listing).where(Listing.id == listing_id)).first() is None
    assert session.exec(select(Photo).where(Photo.listing_id == listing_id)).all() == []


def test_invalid_status_raises_validation_error() -> None:
    with pytest.raises(ValueError, match="status"):
        Listing(seller_id=1, title="x", description="y", status="invalid")


def test_default_status_is_active() -> None:
    listing = Listing(seller_id=1, title="x", description="y")
    assert listing.status == "active"


def test_explicit_valid_statuses_accepted() -> None:
    for status in ("active", "sold", "withdrawn"):
        listing = Listing(seller_id=1, title="x", description="y", status=status)
        assert listing.status == status
