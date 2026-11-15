"""CHK-001..004: real appointment transitions and therapist-owned completion."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.routers import appointments


START = datetime(2026, 9, 1, 10, tzinfo=timezone.utc)
CHILD = ObjectId("0000000000000000000000c1")
THERAPIST = ObjectId("0000000000000000000000d1")
OTHER = ObjectId("0000000000000000000000d2")
CAREGIVER_USER = {"_id": CHILD, "role": "user", "full_name": "Caregiver"}
THERAPIST_USER = {"_id": THERAPIST, "role": "therapist", "full_name": "Therapist"}


def matches(doc, query):
    for key, value in query.items():
        actual = doc.get(key)
        if isinstance(value, dict) and "$in" in value:
            if actual not in value["$in"]:
                return False
        elif isinstance(value, dict) and "$gte" in value:
            if actual is None or actual < value["$gte"]:
                return False
        elif actual != value:
            return False
    return True


class Rows:
    def __init__(self, docs=()):
        self.docs = [dict(doc) for doc in docs]

    async def find_one(self, query, **kwargs):
        return next((doc for doc in self.docs if matches(doc, query)), None)

    async def insert_one(self, doc):
        saved = dict(doc, _id=ObjectId())
        self.docs.append(saved)
        return SimpleNamespace(inserted_id=saved["_id"])

    async def find_one_and_update(self, query, update, **kwargs):
        row = await self.find_one(query)
        if row is None:
            return None
        for key, value in update.get("$set", {}).items():
            row[key] = value
        for key in update.get("$unset", {}):
            row.pop(key, None)
        return row

    def find(self, query):
        rows = [row for row in self.docs if matches(row, query)]

        class Cursor:
            async def to_list(self, length):
                return rows[:length]

        return Cursor()


class Database:
    def __init__(self):
        self.users = Rows([
            dict(CAREGIVER_USER, therapist_id=str(THERAPIST), therapist_assigned_at=START),
            THERAPIST_USER, {"_id": OTHER, "role": "therapist"},
        ])
        self.appointments = Rows()


@pytest.fixture
def database(monkeypatch):
    db = Database()
    monkeypatch.setattr(appointments, "get_database", lambda: db)
    monkeypatch.setattr(appointments, "now", lambda: START + timedelta(days=15))

    async def no_side_effect(*args, **kwargs):
        return None

    monkeypatch.setattr(appointments, "push_notification", no_side_effect)
    monkeypatch.setattr(appointments, "audit", no_side_effect)
    return db


@pytest.mark.asyncio
async def test_chk002_booking_uses_current_assigned_therapist_and_open_key(database):
    payload = appointments.CheckupCreate(scheduled_at=START + timedelta(days=16), mode="online")
    booked = await appointments.book_checkup(payload, CAREGIVER_USER)
    assert booked["kind"] == "checkup"
    assert booked["therapist_id"] == str(THERAPIST)
    assert booked["status"] == "pending"
    assert booked["open_checkup_key"] == str(CHILD)
    with pytest.raises(HTTPException) as duplicate:
        await appointments.book_checkup(payload, CAREGIVER_USER)
    assert duplicate.value.status_code == 409


@pytest.mark.asyncio
async def test_chk002_caregiver_cannot_complete_even_own_checkup(database):
    booked = await appointments.book_checkup(
        appointments.CheckupCreate(scheduled_at=START + timedelta(days=16), mode="online"), CAREGIVER_USER)
    with pytest.raises(HTTPException) as error:
        await appointments.update_status(booked["id"], appointments.StatusUpdate(status="completed"), CAREGIVER_USER)
    assert error.value.status_code == 403
    assert database.appointments.docs[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_chk002_therapist_completion_waits_for_visit_then_resets_clock(database, monkeypatch):
    booked = await appointments.book_checkup(
        appointments.CheckupCreate(scheduled_at=START + timedelta(days=16), mode="online"), CAREGIVER_USER)
    await appointments.update_status(booked["id"], appointments.StatusUpdate(status="confirmed"), THERAPIST_USER)
    with pytest.raises(HTTPException) as early:
        await appointments.update_status(booked["id"], appointments.StatusUpdate(status="completed"), THERAPIST_USER)
    assert early.value.status_code == 400
    monkeypatch.setattr(appointments, "now", lambda: START + timedelta(days=16, hours=1))
    completed = await appointments.update_status(booked["id"], appointments.StatusUpdate(status="completed"), THERAPIST_USER)
    assert completed["completed_by"] == str(THERAPIST)
    status = await appointments.my_checkup_status(CAREGIVER_USER)
    assert status["state"] == "not_due"
    assert status["due_at"] == "2026-10-01T11:00:00+00:00"


@pytest.mark.asyncio
async def test_chk002_reassignment_invalidates_old_therapist_completion(database):
    booked = await appointments.book_checkup(
        appointments.CheckupCreate(scheduled_at=START + timedelta(days=16), mode="online"), CAREGIVER_USER)
    database.users.docs[0]["therapist_id"] = str(OTHER)
    with pytest.raises(HTTPException) as stale:
        await appointments.update_status(booked["id"], appointments.StatusUpdate(status="confirmed"), THERAPIST_USER)
    assert stale.value.status_code == 403
