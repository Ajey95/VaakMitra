"""Registration validation, success, and failure handling tests."""
import pytest
from fastapi import FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from pymongo.errors import AutoReconnect
from pydantic import ValidationError
from bson import ObjectId

from app.models.user import LoginRequest, UserCreate
from app.routers import auth


def registration_payload(**overrides):
    values = {
        "full_name": "Test Parent",
        "child_name": "Test Child",
        "child_age": 7,
        "email": "test@example.com",
        "password": "TestPassword1!",
        "confirm_password": "TestPassword1!",
        "language": "Tamil",
    }
    values.update(overrides)
    return values


@pytest.mark.parametrize(
    ("override", "value"),
    [
        ("full_name", "   "),
        ("child_name", "\t "),
        ("language", "Klingon"),
        ("password", "A1!" + "x" * 126),
    ],
)
def test_registration_schema_rejects_untrusted_profile_values(override, value):
    payload = registration_payload(**{override: value})
    if override == "password":
        payload["confirm_password"] = value

    with pytest.raises(ValidationError):
        UserCreate(**payload)


def test_registration_schema_trims_names_and_normalizes_email():
    user = UserCreate(**registration_payload(
        full_name="  Test Parent  ",
        child_name="  Test Child  ",
        email="  Parent@Example.COM  ",
    ))

    assert user.full_name == "Test Parent"
    assert user.child_name == "Test Child"
    assert str(user.email) == "parent@example.com"


@pytest.mark.asyncio
async def test_register_returns_complete_user_and_normalizes_duplicate_lookup(monkeypatch):
    inserted_id = ObjectId()

    class Users:
        def __init__(self):
            self.query = None
            self.inserted = None

        async def find_one(self, query):
            self.query = query
            return None

        async def insert_one(self, document):
            self.inserted = document
            return type("InsertResult", (), {"inserted_id": inserted_id})()

    users = Users()
    monkeypatch.setattr(auth, "ensure_database", lambda: _async_value(type("Database", (), {"users": users})()))
    monkeypatch.setattr(auth, "hash_password", lambda _password: "safe-hash")
    monkeypatch.setattr(auth, "create_access_token", lambda data: f"token-for-{data['sub']}")

    response = Response()
    result = await auth.register(UserCreate(**registration_payload(email="Parent@Example.COM")), response)

    assert users.query == {"email": "parent@example.com"}
    assert users.inserted["email"] == "parent@example.com"
    assert result["user"] == {
        "id": str(inserted_id),
        "email": "parent@example.com",
        "full_name": "Test Parent",
        "child_name": "Test Child",
        "child_age": 7,
        "language": "Tamil",
        "role": "user",
        "total_sessions": 0,
        "total_stars": 0,
    }
    assert response.headers.get("set-cookie")


async def _async_value(value):
    return value


@pytest.mark.asyncio
async def test_demo_login_succeeds_when_database_is_unavailable(monkeypatch):
    def unavailable_database():
        raise HTTPException(status_code=503, detail="Database unavailable")

    monkeypatch.setattr(auth, "get_database", unavailable_database)
    monkeypatch.setattr(auth, "create_access_token", lambda data: f"token-for-{data['sub']}")

    response = Response()
    result = await auth.login(
        LoginRequest(email="demo@speakeasy.app", password="Demo@1234"),
        response,
    )

    assert result["user"] == {
        "email": "demo@speakeasy.app",
        "full_name": "Demo Parent",
        "child_name": "Kavi",
        "child_age": 7,
        "role": "user",
        "total_sessions": 12,
        "total_stars": 180,
        "language": "Tamil",
        "is_demo": True,
    }
    assert result["access_token"] == "token-for-demo@speakeasy.app"
    assert response.headers.get("set-cookie")


@pytest.mark.asyncio
async def test_non_demo_login_still_requires_database(monkeypatch):
    def unavailable_database():
        raise HTTPException(status_code=503, detail="Database unavailable")

    monkeypatch.setattr(auth, "get_database", unavailable_database)

    with pytest.raises(HTTPException) as error:
        await auth.login(
            LoginRequest(email="person@example.com", password="Password1!"),
            Response(),
        )

    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_register_rejects_case_insensitive_duplicate_email(monkeypatch):
    class Users:
        async def find_one(self, query):
            return {"email": query["email"]} if query["email"] == "parent@example.com" else None

    database = type("Database", (), {"users": Users()})()
    monkeypatch.setattr(auth, "ensure_database", lambda: _async_value(database))

    with pytest.raises(HTTPException) as error:
        await auth.register(UserCreate(**registration_payload(email="Parent@Example.COM")), Response())

    assert error.value.status_code == 400
    assert error.value.detail == "Email already registered"


def test_registration_http_contract_sets_cookie_and_rejects_invalid_profile(monkeypatch):
    inserted_id = ObjectId()

    class Users:
        async def find_one(self, _query):
            return None

        async def insert_one(self, _document):
            return type("InsertResult", (), {"inserted_id": inserted_id})()

    database = type("Database", (), {"users": Users()})()
    monkeypatch.setattr(auth, "ensure_database", lambda: _async_value(database))
    monkeypatch.setattr(auth, "hash_password", lambda _password: "safe-hash")
    monkeypatch.setattr(auth, "create_access_token", lambda _data=None, **_kwargs: "http-only-token")

    app = FastAPI()
    app.include_router(auth.router)
    with TestClient(app) as client:
        created = client.post("/api/auth/register", json=registration_payload())
        invalid = client.post("/api/auth/register", json=registration_payload(full_name="   "))

    assert created.status_code == 201
    assert created.json()["user"]["id"] == str(inserted_id)
    assert created.cookies.get(auth.settings.ACCESS_COOKIE_NAME) == "http-only-token"
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_register_returns_service_unavailable_when_database_drops(monkeypatch):
    class FailingUsers:
        async def find_one(self, _query):
            raise AutoReconnect("database connection dropped")

    class FailingDatabase:
        users = FailingUsers()

    async def fake_ensure_database():
        return FailingDatabase()

    monkeypatch.setattr(auth, "ensure_database", fake_ensure_database)

    payload = UserCreate(
        full_name="Test Parent",
        child_name="Test Child",
        child_age=7,
        email="test@example.com",
        password="TestPassword1!",
        confirm_password="TestPassword1!",
        language="Tamil",
    )

    with pytest.raises(HTTPException) as error:
        await auth.register(payload, Response())

    assert error.value.status_code == 503
