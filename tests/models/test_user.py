"""Tests for the User model."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import User


def test_persist_and_retrieve_by_email(session: Session) -> None:
    user = User(email="alice@example.com", password_hash="$2b$12$placeholder")
    session.add(user)
    session.commit()

    found = session.exec(select(User).where(User.email == "alice@example.com")).one()
    assert found.id is not None
    assert found.email == "alice@example.com"
    assert found.is_verified is False
    assert found.password_hash == "$2b$12$placeholder"


def test_email_normalized_to_lowercase_and_stripped(session: Session) -> None:
    user = User(email="  ALICE@Example.COM ", password_hash="$2b$12$placeholder")
    session.add(user)
    session.commit()
    assert user.email == "alice@example.com"


def test_duplicate_email_raises_integrity_error(session: Session) -> None:
    session.add(User(email="alice@example.com", password_hash="hash1"))
    session.commit()

    session.add(User(email="alice@example.com", password_hash="hash2"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_duplicate_email_case_insensitive(session: Session) -> None:
    """Validator lowercases on insert, so 'ALICE@..' duplicates 'alice@..'."""
    session.add(User(email="alice@example.com", password_hash="hash1"))
    session.commit()

    session.add(User(email="ALICE@EXAMPLE.COM", password_hash="hash2"))
    with pytest.raises(IntegrityError):
        session.commit()
