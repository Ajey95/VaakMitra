"""Appointments router — booking therapy sessions with therapists.

Backs the Appointments page (web + Android). A parent books a slot with a
therapist; the therapist confirms/completes; either side can cancel. Reminders
land in the notification centre.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_therapist, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now
from .notifications import push_notification
from ..vaakmitra_word.checkups import checkup_status

router = APIRouter(prefix="/api/appointments", tags=["appointments"])

STATUSES = ["pending", "confirmed", "completed", "cancelled", "no_show"]
MODES = ["online", "in_person"]


class AppointmentCreate(BaseModel):
    therapist_id: str
    scheduled_at: datetime
    duration_min: int = Field(default=30, ge=10, le=180)
    mode: str = Field(default="online")
    reason: Optional[str] = Field(default=None, max_length=1000)


class CheckupCreate(BaseModel):
    scheduled_at: datetime
    duration_min: int = Field(default=30, ge=10, le=180)
    mode: Literal["online", "in_person"] = "online"

    @field_validator("scheduled_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("scheduled_at needs a timezone")
        return value.astimezone(timezone.utc)


class AppointmentReschedule(BaseModel):
    scheduled_at: datetime
    duration_min: Optional[int] = Field(default=None, ge=10, le=180)


class StatusUpdate(BaseModel):
    status: str
    note: Optional[str] = None


def _is_participant(appt: dict, user: dict) -> bool:
    uid = str(user["_id"])
    return uid in (appt.get("user_id"), appt.get("therapist_id")) or user.get("role") == "admin"


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _active_slot_key(therapist_id: str, at: datetime) -> str:
    return f"{therapist_id}:{_utc(at).isoformat()}"


async def _current_checkup_child(db, appt: dict) -> dict:
    child = await db.users.find_one({"_id": oid(appt["user_id"])})
    if not child or child.get("therapist_id") != appt.get("therapist_id"):
        raise HTTPException(status_code=403, detail="assigned_therapist_changed")
    return child


@router.get("/checkup-status")
async def my_checkup_status(current_user: dict = Depends(get_current_user)):
    """CHK-001/003: caregiver-visible 14-day clock, never a practice lock."""
    if current_user.get("role") != "user":
        raise HTTPException(status_code=403, detail="caregiver_account_required")
    db = get_database()
    child = await db.users.find_one({"_id": current_user["_id"]})
    if not child:
        raise HTTPException(status_code=404, detail="child_profile_not_found")
    rows = await db.appointments.find({"user_id": str(current_user["_id"])}).to_list(length=1000)
    return checkup_status(child.get("therapist_id"), child.get("therapist_assigned_at"), rows, now())


@router.post("/checkups")
async def book_checkup(payload: CheckupCreate, current_user: dict = Depends(get_current_user)):
    """CHK-002/004: request only the assigned therapist; no auto-booking."""
    if current_user.get("role") != "user":
        raise HTTPException(status_code=403, detail="caregiver_account_required")
    db = get_database()
    child = await db.users.find_one({"_id": current_user["_id"]})
    if not child or not child.get("therapist_id"):
        raise HTTPException(status_code=409, detail="assigned_therapist_required")
    therapist_id = child["therapist_id"]
    therapist = await db.users.find_one({"_id": oid(therapist_id)})
    if not therapist or therapist.get("role") != "therapist":
        raise HTTPException(status_code=409, detail="assigned_therapist_unavailable")
    if _utc(payload.scheduled_at) <= _utc(now()):
        raise HTTPException(status_code=400, detail="appointment_must_be_future")
    user_id = str(current_user["_id"])
    if await db.appointments.find_one({"user_id": user_id, "kind": "checkup",
                                       "status": {"$in": ["pending", "confirmed"]}}):
        raise HTTPException(status_code=409, detail="checkup_request_already_open")
    if await db.appointments.find_one({"therapist_id": therapist_id,
                                       "scheduled_at": payload.scheduled_at,
                                       "status": {"$in": ["pending", "confirmed"]}}):
        raise HTTPException(status_code=409, detail="therapist_slot_unavailable")
    created = now()
    doc = {
        "user_id": user_id, "therapist_id": therapist_id,
        "therapist_name": therapist.get("full_name"), "kind": "checkup",
        "scheduled_at": payload.scheduled_at, "duration_min": payload.duration_min,
        "mode": payload.mode, "reason": None, "note": None,
        "status": "pending", "open_checkup_key": user_id,
        "active_slot_key": _active_slot_key(therapist_id, payload.scheduled_at),
        "created_at": created, "updated_at": created,
    }
    try:
        result = await db.appointments.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="checkup_or_slot_already_open") from exc
    await push_notification(therapist_id, "Checkup request", "A caregiver requested a checkup.",
                            category="appointment", link="/appointments")
    await audit("checkup.requested", current_user, target=str(result.inserted_id))
    return serialize(dict(doc, _id=result.inserted_id))


@router.post("")
async def book(payload: AppointmentCreate, current_user: dict = Depends(get_current_user)):
    """Book an appointment with a therapist."""
    db = get_database()
    therapist = await db.users.find_one({"_id": oid(payload.therapist_id)})
    if not therapist or therapist.get("role") not in ("therapist", "admin"):
        raise HTTPException(status_code=404, detail="Therapist not found")
    if _utc(payload.scheduled_at) < _utc(now()):
        raise HTTPException(status_code=400, detail="Cannot book a slot in the past")
    # Prevent double-booking the same therapist at the same instant.
    clash = await db.appointments.find_one({
        "therapist_id": str(therapist["_id"]),
        "scheduled_at": payload.scheduled_at,
        "status": {"$in": ["pending", "confirmed"]},
    })
    if clash:
        raise HTTPException(status_code=409, detail="Therapist is not available at that time")
    doc = {
        "user_id": str(current_user["_id"]),
        "user_name": current_user.get("full_name"),
        "child_name": current_user.get("child_name"),
        "therapist_id": str(therapist["_id"]),
        "therapist_name": therapist.get("full_name"),
        "scheduled_at": payload.scheduled_at,
        "duration_min": payload.duration_min,
        "mode": payload.mode if payload.mode in MODES else "online",
        "reason": payload.reason,
        "status": "pending", "kind": "ordinary",
        "active_slot_key": _active_slot_key(str(therapist["_id"]), payload.scheduled_at),
        "note": None,
        "created_at": now(),
        "updated_at": now(),
    }
    try:
        result = await db.appointments.insert_one(doc)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="therapist_slot_unavailable") from exc
    await push_notification(
        str(therapist["_id"]), "New appointment request",
        f"{current_user.get('full_name')} requested a session.",
        category="appointment", link="/appointments",
    )
    await audit("appointment.book", current_user, target=str(result.inserted_id))
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("")
async def my_appointments(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    upcoming: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """List the caller's appointments (as parent or therapist)."""
    db = get_database()
    uid = str(current_user["_id"])
    query = {"$or": [{"user_id": uid}, {"therapist_id": uid}]}
    if current_user.get("role") == "admin":
        query = {}
    if status in STATUSES:
        query["status"] = status
    if upcoming:
        query["scheduled_at"] = {"$gte": now()}
    return await paginate(db.appointments, query, page, limit, sort_field="scheduled_at", sort_dir=1)


@router.get("/available-therapists")
async def available_therapists(current_user: dict = Depends(get_current_user)):
    """List therapists a parent can book with."""
    db = get_database()
    therapists = await db.users.find(
        {"role": "therapist"},
        {"full_name": 1, "email": 1, "avatar_url": 1, "medical": 1},
    ).to_list(length=500)
    return serialize(therapists)


@router.get("/{appointment_id}")
async def get_appointment(appointment_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch a single appointment (participants only)."""
    db = get_database()
    appt = await db.appointments.find_one({"_id": oid(appointment_id)})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if not _is_participant(appt, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    return serialize(appt)


@router.patch("/{appointment_id}/reschedule")
async def reschedule(appointment_id: str, payload: AppointmentReschedule, current_user: dict = Depends(get_current_user)):
    """Reschedule an appointment to a new time."""
    db = get_database()
    appt = await db.appointments.find_one({"_id": oid(appointment_id)})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if not _is_participant(appt, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    if appt.get("kind") == "checkup":
        await _current_checkup_child(db, appt)
        if current_user.get("role") not in {"user", "therapist"}:
            raise HTTPException(status_code=403, detail="checkup_participant_required")
    if appt["status"] not in {"pending", "confirmed"}:
        raise HTTPException(status_code=409, detail="appointment_not_open")
    if _utc(payload.scheduled_at) < _utc(now()):
        raise HTTPException(status_code=400, detail="Cannot reschedule to the past")
    clash = await db.appointments.find_one({
        "therapist_id": appt["therapist_id"], "scheduled_at": payload.scheduled_at,
        "status": {"$in": ["pending", "confirmed"]},
    })
    if clash and str(clash["_id"]) != appointment_id:
        raise HTTPException(status_code=409, detail="therapist_slot_unavailable")
    updates = {"scheduled_at": payload.scheduled_at, "status": "pending", "updated_at": now(),
               "active_slot_key": _active_slot_key(appt["therapist_id"], payload.scheduled_at)}
    if payload.duration_min:
        updates["duration_min"] = payload.duration_min
    try:
        changed = await db.appointments.find_one_and_update(
            {"_id": oid(appointment_id), "status": appt["status"]}, {"$set": updates})
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="therapist_slot_unavailable") from exc
    if changed is None:
        raise HTTPException(status_code=409, detail="appointment_changed")
    other = appt["therapist_id"] if str(current_user["_id"]) == appt["user_id"] else appt["user_id"]
    await push_notification(other, "Appointment rescheduled", "A session time has changed.", category="appointment", link="/appointments")
    return serialize(await db.appointments.find_one({"_id": oid(appointment_id)}))


@router.patch("/{appointment_id}/status")
async def update_status(appointment_id: str, payload: StatusUpdate, current_user: dict = Depends(get_current_user)):
    """Confirm / complete / cancel / mark no-show."""
    db = get_database()
    appt = await db.appointments.find_one({"_id": oid(appointment_id)})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if not _is_participant(appt, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    if payload.status not in STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if appt.get("kind") == "checkup":
        await _current_checkup_child(db, appt)
        if current_user.get("role") not in {"user", "therapist"}:
            raise HTTPException(status_code=403, detail="checkup_participant_required")
        if payload.note:
            raise HTTPException(status_code=400, detail="checkup_free_text_not_allowed")
    actor_id = str(current_user["_id"])
    if payload.status in {"confirmed", "completed", "no_show"}:
        if current_user.get("role") != "therapist" or actor_id != appt["therapist_id"]:
            raise HTTPException(status_code=403, detail="therapist_transition_required")
    elif payload.status == "cancelled":
        if actor_id not in {appt["user_id"], appt["therapist_id"]}:
            raise HTTPException(status_code=403, detail="participant_required")
    else:
        raise HTTPException(status_code=400, detail="invalid_status_transition")
    allowed = {"pending": {"confirmed", "cancelled"},
               "confirmed": {"completed", "cancelled", "no_show"}}
    if payload.status not in allowed.get(appt["status"], set()):
        raise HTTPException(status_code=409, detail="invalid_status_transition")
    if payload.status in {"completed", "no_show"} and _utc(now()) < _utc(appt["scheduled_at"]):
        raise HTTPException(status_code=400, detail="appointment_has_not_started")
    updates = {"status": payload.status, "updated_at": now()}
    if payload.status == "completed":
        updates.update({"completed_at": now(), "completed_by": actor_id})
    unsets = {"active_slot_key": "", "open_checkup_key": ""} if payload.status in {"completed", "cancelled", "no_show"} else {}
    changed = await db.appointments.find_one_and_update(
        {"_id": oid(appointment_id), "status": appt["status"]},
        {"$set": updates, "$unset": unsets},
    )
    if changed is None:
        raise HTTPException(status_code=409, detail="appointment_changed")
    other = appt["therapist_id"] if str(current_user["_id"]) == appt["user_id"] else appt["user_id"]
    await push_notification(other, f"Appointment {payload.status}", f"A session is now {payload.status}.", category="appointment", link="/appointments")
    await audit("appointment.status", current_user, target=appointment_id,
                meta={"status": payload.status, "kind": appt.get("kind", "ordinary")})
    return serialize(await db.appointments.find_one({"_id": oid(appointment_id)}))


@router.delete("/{appointment_id}")
async def cancel(appointment_id: str, current_user: dict = Depends(get_current_user)):
    """Cancel (soft — sets status=cancelled) an appointment."""
    db = get_database()
    appt = await db.appointments.find_one({"_id": oid(appointment_id)})
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if not _is_participant(appt, current_user):
        raise HTTPException(status_code=403, detail="Access denied")
    if appt.get("kind") == "checkup":
        await _current_checkup_child(db, appt)
        if current_user.get("role") not in {"user", "therapist"}:
            raise HTTPException(status_code=403, detail="checkup_participant_required")
    if appt["status"] not in {"pending", "confirmed"}:
        raise HTTPException(status_code=409, detail="appointment_not_open")
    changed = await db.appointments.find_one_and_update(
        {"_id": oid(appointment_id), "status": appt["status"]},
        {"$set": {"status": "cancelled", "updated_at": now()},
         "$unset": {"active_slot_key": "", "open_checkup_key": ""}},
    )
    if changed is None:
        raise HTTPException(status_code=409, detail="appointment_changed")
    await audit("appointment.cancelled", current_user, target=appointment_id)
    return {"message": "Appointment cancelled"}


@router.get("/admin/all")
async def admin_all(page: int = 1, limit: int = 30, status: Optional[str] = None, current_admin: dict = Depends(require_admin)):
    """Admin: list every appointment."""
    db = get_database()
    query = {"status": status} if status in STATUSES else {}
    return await paginate(db.appointments, query, page, limit, sort_field="scheduled_at", sort_dir=-1)
