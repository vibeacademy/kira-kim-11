"""User model.

Single user table for the marketplace — the same row plays both buyer
(searches, favorites, bids) and seller (lists). Identity is by email.
"""

from datetime import UTC, datetime
from typing import Any

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """A registered user account."""

    # `user` is reserved in Postgres; pick a non-reserved table name.
    __tablename__ = "app_user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(max_length=320, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def __init__(self, **data: Any) -> None:
        # SQLite has no CITEXT and SQLModel's `table=True` classes bypass
        # Pydantic validators on instantiation, so normalize the email here.
        # The UNIQUE index on email enforces the deduplication.
        email = data.get("email")
        if isinstance(email, str):
            data["email"] = email.strip().lower()
        super().__init__(**data)
