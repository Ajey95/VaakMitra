"""Calendar router — personal events, practice reminders and a month feed.

Backs the Calendar page. Merges user-created events with their appointments so
the calendar shows one unified timeline.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, oid, now

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

EVENT_TYPES = ["practice", "reminder", "personal", "goal", "milestone"]


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: Optional[str] = Field(default=None, max_length=1000)
    type: str = Field(default="personal")
    start: datetime
    end: Optional[datetime] = None
    all_day: bool = False
    color: Optional[str] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    all_day: Optional[bool] = None
    color: Optional[str] = None
    done: Optional[bool] = None


@router.post("/events")
async def create_event(payload: EventCreate, current_user: dict = Depends(get_current_user)):
    """Create a calendar event."""
    db = get_database()
    doc = {
        "user_id": str(current_user["_id"]),
        "title": payload.title,
        "description": payload.description,
        "type": payload.type if payload.type in EVENT_TYPES else "personal",
        "start": payload.start,
        "end": payload.end,
        "all_day": payload.all_day,
        "color": payload.color,
        "done": False,
        "created_at": now(),
    }
    result = await db.calendar_events.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/events")
async def list_events(
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    include_appointments: bool = True,
    current_user: dict = Depends(get_current_user),
):
    """List events (and optionally appointments) in a date window."""
    db = get_database()
    uid = str(current_user["_id"])
    query = {"user_id": uid}
    if start or end:
        rng = {}
        if start:
            rng["$gte"] = start
        if end:
            rng["$lte"] = end
        query["start"] = rng
    events = await db.calendar_events.find(query).sort("start", 1).to_list(length=1000)
    items = serialize(events)
    if include_appointments:
        appt_query = {"$or": [{"user_id": uid}, {"therapist_id": uid}], "status": {"$in": ["pending", "confirmed"]}}
        if start or end:
            rng = {}
            if start:
                rng["$gte"] = start
            if end:
                rng["$lte"] = end
            appt_query["scheduled_at"] = rng
        appts = await db.appointments.find(appt_query).to_list(length=1000)
        for a in appts:
            items.append({
                "id": str(a["_id"]),
                "title": f"Session: {a.get('therapist_name') or a.get('user_name')}",
                "type": "appointment",
                "start": a["scheduled_at"].isoformat(),
                "end": (a["scheduled_at"] + timedelta(minutes=a.get("duration_min", 30))).isoformat(),
                "color": "#6366f1",
                "source": "appointment",
            })
    return {"events": items}


@router.get("/upcoming")
async def upcoming(days: int = Query(default=7, ge=1, le=90), current_user: dict = Depends(get_current_user)):
    """List events in the next N days (drives the dashboard 'upcoming' widget)."""
    db = get_database()
    window_end = now() + timedelta(days=days)
    events = await db.calendar_events.find({
        "user_id": str(current_user["_id"]),
        "start": {"$gte": now(), "$lte": window_end},
    }).sort("start", 1).to_list(length=100)
    return {"events": serialize(events)}


@router.patch("/events/{event_id}")
async def update_event(event_id: str, payload: EventUpdate, current_user: dict = Depends(get_current_user)):
    """Update an event."""
    db = get_database()
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.calendar_events.update_one(
        {"_id": oid(event_id), "user_id": str(current_user["_id"])}, {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return serialize(await db.calendar_events.find_one({"_id": oid(event_id)}))


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an event."""
    db = get_database()
    result = await db.calendar_events.delete_one({"_id": oid(event_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}
