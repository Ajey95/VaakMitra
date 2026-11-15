"""Health and security middleware contract tests."""
import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main
from app.main import app, health_ready


def test_liveness_has_security_headers():
    with TestClient(app) as client:
        response = client.get("/health/live", headers={"Host": "localhost"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Request-ID"]


def test_readiness_is_503_when_database_reconnect_fails(monkeypatch):
    async def unavailable():
        raise HTTPException(status_code=503, detail="Database unavailable")

    monkeypatch.setattr(main, "ensure_database", unavailable)

    with pytest.raises(HTTPException) as error:
        asyncio.run(health_ready())
    assert error.value.status_code == 503
    assert error.value.detail == "database_unavailable"


def test_readiness_recovers_a_stale_database_connection(monkeypatch):
    attempts = []

    async def reconnect():
        attempts.append("ping")
        return object()

    monkeypatch.setattr(main, "ensure_database", reconnect)

    assert asyncio.run(health_ready()) == {"status": "ready", "database": "ok"}
    assert attempts == ["ping"]
