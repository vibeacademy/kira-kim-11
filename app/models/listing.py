"""Listing and Photo models for the marketplace catalog.

A `Listing` is a single stuffed-animal-for-sale post owned by a `User`
(via `seller_id`). A `Listing` has zero or more `Photo` rows; deleting
a `Listing` cascades to its `Photo`s at both the ORM and DB level.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, ForeignKey, Index, Integer
from sqlmodel import Field, Relationship, SQLModel

VALID_STATUSES = frozenset({"active", "sold", "withdrawn"})


class Listing(SQLModel, table=True):
    """A stuffed-animal listing posted by a seller."""

    id: int | None = Field(default=None, primary_key=True)
    seller_id: int = Field(foreign_key="app_user.id", index=True)
    title: str = Field(max_length=200)
    description: str
    era: str | None = Field(default=None, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=100)
    condition: str | None = Field(default=None, max_length=100)
    status: str = Field(default="active", max_length=20)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    photos: list["Photo"] = Relationship(
        back_populates="listing",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "Photo.sort_order",
        },
    )

    def __init__(self, **data: Any) -> None:
        # SQLModel `table=True` classes bypass Pydantic validators on
        # instantiation, so enforce the status whitelist here. A Postgres
        # ENUM was intentionally avoided per the ticket guardrails — string
        # + app-level whitelist keeps migrations cheap when statuses change.
        status = data.get("status", "active")
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Listing.status must be one of {sorted(VALID_STATUSES)}, got {status!r}"
            )
        super().__init__(**data)


class Photo(SQLModel, table=True):
    """A photo attached to a listing."""

    __table_args__ = (Index("ix_photo_listing_id_sort_order", "listing_id", "sort_order"),)

    id: int | None = Field(default=None, primary_key=True)
    listing_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("listing.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    gcs_key: str = Field(max_length=500)
    thumb_key: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0)

    listing: Listing | None = Relationship(back_populates="photos")
