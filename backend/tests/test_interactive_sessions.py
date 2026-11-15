"""Security and aggregation contracts for child interaction reporting."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import interactive_sessions
from app.routers.interactive_sessions import build_interactive_summary
from app.utils.jwt_handler import get_current_user


NOW = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)


def valid_payload(**overrides):
    payload = {
        "activity_id": "breath-balloon",
        "activity_type": "arcade",
        "started_at": "2026-08-01T11:58:00Z",
        "completed_at": "2026-08-01T12:00:00Z",
        "communication_turns": 3,
        "successful_turns": 2,
        "attempts": 4,
        "assistance_counts": {
            "independent": 2,
            "verbal_prompt": 1,
            "visual_prompt": 0,
            "modelled": 0,
            "skipped": 0,
        },
        "duration_ms": 120_000,
        "effort_points": 12,
    }
    payload.update(overrides)
    return payload


class InsertResult:
    inserted_id = "session-1"


class FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, *_args):
        return self

    def limit(self, amount):
        self.rows = self.rows[:amount]
        return self

    async def to_list(self, length):
        return self.rows[:length]


class FakeCollection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def insert_one(self, document):
        self.rows.append(dict(document))
        return InsertResult()

    def find(self, query):
        rows = self.rows
        if "user_id" in query:
            rows = [row for row in rows if row.get("user_id") == query["user_id"]]
        minimum = query.get("created_at", {}).get("$gte")
        if minimum:
            rows = [row for row in rows if row.get("created_at") and row["created_at"] >= minimum]
        return FakeCursor(rows)


class FakeDatabase:
    def __init__(self, rows=None):
        self.interactive_sessions = FakeCollection(rows)


def isolated_app(user=None):
    app = FastAPI()
    app.include_router(interactive_sessions.router)
    if user:
        app.dependency_overrides[get_current_user] = lambda: user
    return app


def test_create_requires_authentication():
    with TestClient(isolated_app()) as client:
        response = client.post("/api/interactive-sessions", json=valid_payload())
    assert response.status_code == 401


@pytest.mark.parametrize("private_field", ["audio", "video", "transcript", "frames", "user_id"])
def test_create_rejects_private_media_transcripts_and_client_ownership(private_field):
    with TestClient(isolated_app({"_id": "child-1"})) as client:
        response = client.post(
            "/api/interactive-sessions",
            json=valid_payload(**{private_field: "must-not-be-stored"}),
        )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("communication_turns", 101),
        ("successful_turns", -1),
        ("attempts", 301),
        ("duration_ms", 3_600_001),
        ("effort_points", 10_001),
    ],
)
def test_create_rejects_out_of_range_counts(field, value):
    with TestClient(isolated_app({"_id": "child-1"})) as client:
        response = client.post("/api/interactive-sessions", json=valid_payload(**{field: value}))
    assert response.status_code == 422


def test_create_uses_authenticated_owner_and_stores_only_safe_fields(monkeypatch):
    database = FakeDatabase()
    monkeypatch.setattr(interactive_sessions, "get_database", lambda: database)

    with TestClient(isolated_app({"_id": "child-7", "child_name": "Maya"})) as client:
        response = client.post("/api/interactive-sessions", json=valid_payload())

    assert response.status_code == 201
    assert response.json() == {"id": "session-1", "status": "recorded"}
    stored = database.interactive_sessions.rows[0]
    assert stored["user_id"] == "child-7"
    assert stored["activity_id"] == "breath-balloon"
    assert set(stored).isdisjoint({"audio", "video", "transcript", "frames", "child_name"})


def test_empty_summary_is_truthful():
    assert build_interactive_summary([], NOW) == {
        "sessions_this_week": 0,
        "communication_turns": 0,
        "independent_percentage": 0,
        "most_practised_activity": None,
        "assistance_trend": [],
        "recommendation": "Complete a Play & Practice activity to begin the private progress summary.",
    }


def test_summary_aggregates_only_the_authenticated_users_recent_sessions(monkeypatch):
    rows = [
        {
            **valid_payload(activity_id="river-rescue", activity_type="quest"),
            "user_id": "child-7",
            "created_at": NOW - timedelta(days=1),
            "communication_turns": 5,
            "assistance_counts": {"independent": 4, "verbal_prompt": 1, "visual_prompt": 0, "modelled": 0, "skipped": 0},
        },
        {
            **valid_payload(activity_id="river-rescue", activity_type="quest"),
            "user_id": "child-7",
            "created_at": NOW - timedelta(days=2),
            "communication_turns": 3,
            "assistance_counts": {"independent": 1, "verbal_prompt": 0, "visual_prompt": 1, "modelled": 1, "skipped": 0},
        },
        {**valid_payload(), "user_id": "another-child", "created_at": NOW - timedelta(hours=2)},
    ]
    database = FakeDatabase(rows)
    monkeypatch.setattr(interactive_sessions, "get_database", lambda: database)
    monkeypatch.setattr(interactive_sessions, "utc_now", lambda: NOW)

    with TestClient(isolated_app({"_id": "child-7"})) as client:
        response = client.get("/api/interactive-sessions/summary")

    assert response.status_code == 200
    summary = response.json()
    assert summary["sessions_this_week"] == 2
    assert summary["communication_turns"] == 8
    assert summary["independent_percentage"] == 63
    assert summary["most_practised_activity"] == "river-rescue"
    assert len(summary["assistance_trend"]) == 2
    assert summary["assistance_trend"][0]["date"] < summary["assistance_trend"][1]["date"]
