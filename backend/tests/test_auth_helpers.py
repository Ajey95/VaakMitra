"""Unit tests for auth password hashing and contact validation."""
import pytest
from pydantic import ValidationError

from app.routers.auth import hash_password, verify_password
from app.routers.contact import ContactRequest


def test_hash_password_is_not_plaintext():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert hashed.startswith("$2")  # bcrypt prefix


def test_verify_password_roundtrip():
    hashed = hash_password("CorrectHorse9")
    assert verify_password("CorrectHorse9", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_hash_is_salted_unique():
    assert hash_password("samepass") != hash_password("samepass")


def test_contact_request_valid():
    c = ContactRequest(name="Asha", email="asha@example.com", message="Hello there")
    assert c.email == "asha@example.com"


def test_contact_request_rejects_bad_email():
    with pytest.raises(ValidationError):
        ContactRequest(name="Asha", email="not-an-email", message="Hi")


def test_contact_request_rejects_empty_message():
    with pytest.raises(ValidationError):
        ContactRequest(name="Asha", email="asha@example.com", message="")
