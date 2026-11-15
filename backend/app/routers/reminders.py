"""Reminders router — scheduled practice reminders.

Users set reminders (daily practice, appointment prep). A scheduler/cron would
fire due reminders into the notification centre; the ``due`` endpoint exposes
what is ready to fire and can be called by that job.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import timedelta
from ..database import get_database
from ..utils.jwt_handler import get_current_user
from ..utils.mongo import serialize, oid, now
from .notifications import push_notification

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    time_of_day: str = Field(description="HH:MM 24h")
    days: List[str] = Field(default_factory=lambda: ["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
    enabled: bool = True


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    time_of_day: Optional[str] = None
    days: Optional[List[str]] = None
    enabled: Optional[bool] = None


@router.post("")
async def create_reminder(payload: ReminderCreate, current_user: dict = Depends(get_current_user)):
    """Create a recurring practice reminder."""
    db = get_database()
    doc = {"user_id": str(current_user["_id"]), **payload.model_dump(), "last_fired": None, "created_at": now()}
    result = await db.reminders.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("")
async def list_reminders(current_user: dict = Depends(get_current_user)):
    """List the caller's reminders."""
    db = get_database()
    rows = await db.reminders.find({"user_id": str(current_user["_id"])}).sort("created_at", -1).to_list(length=100)
    return {"reminders": serialize(rows)}


@router.patch("/{reminder_id}")
async def update_reminder(reminder_id: str, payload: ReminderUpdate, current_user: dict = Depends(get_current_user)):
    """Update a reminder (time, days, enabled)."""
    db = get_database()
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.reminders.update_one({"_id": oid(reminder_id), "user_id": str(current_user["_id"])}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return serialize(await db.reminders.find_one({"_id": oid(reminder_id)}))


@router.delete("/{reminder_id}")
async def delete_reminder(reminder_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a reminder."""
    db = get_database()
    result = await db.reminders.delete_one({"_id": oid(reminder_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"message": "Deleted"}


@router.post("/{reminder_id}/fire")
async def fire_reminder(reminder_id: str, current_user: dict = Depends(get_current_user)):
    """Manually fire a reminder now (drops it into notifications)."""
    db = get_database()
    rem = await db.reminders.find_one({"_id": oid(reminder_id), "user_id": str(current_user["_id"])})
    if not rem:
        raise HTTPException(status_code=404, detail="Reminder not found")
    await push_notification(str(current_user["_id"]), rem["title"], "Time to practise!", category="reminder", link="/training")
    await db.reminders.update_one({"_id": oid(reminder_id)}, {"$set": {"last_fired": now()}})
    return {"message": "Reminder fired"}
