"""Tests for resolve_user_id access logic."""
import pytest
from fastapi import HTTPException

from app.utils.jwt_handler import resolve_user_id


USER = {"_id": "507f1f77bcf86cd799439011", "email": "a@b.com", "role": "user"}
ADMIN = {"_id": "aaaaaaaaaaaaaaaaaaaaaaaa", "email": "admin@b.com", "role": "admin"}


def test_me_resolves_to_self():
    assert resolve_user_id(USER, "me") == USER["_id"]


def test_email_resolves_to_self():
    assert resolve_user_id(USER, "a@b.com") == USER["_id"]


def test_own_id_resolves():
    assert resolve_user_id(USER, USER["_id"]) == USER["_id"]


def test_other_user_denied():
    with pytest.raises(HTTPException) as exc:
        resolve_user_id(USER, "someone-elses-id")
    assert exc.value.status_code == 403


def test_admin_can_request_any():
    assert resolve_user_id(ADMIN, "any-user-id") == "any-user-id"
