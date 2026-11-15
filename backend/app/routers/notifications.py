"""Notifications router — per-user notification centre.

Backs the Notifications page (web + Android). Notifications are created by the
system (session results, achievements, appointment reminders, announcements) and
read/managed by the owning user. Admins can broadcast to many users at once.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# Notification categories the UI can filter/group by.
CATEGORIES = ["system", "achievement", "reminder", "appointment", "announcement", "progress", "social"]


class NotificationCreate(BaseModel):
    user_id: str
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(default="", max_length=2000)
    category: str = Field(default="system")
    icon: Optional[str] = None
    link: Optional[str] = None


class BroadcastCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(default="", max_length=2000)
    category: str = Field(default="announcement")
    role: Optional[str] = Field(default="user", description="Target role, or 'all'")


async def push_notification(user_id: str, title: str, body: str = "", category: str = "system", icon: str = None, link: str = None):
    """Helper other routers call to drop a notification for a user."""
    db = get_database()
    doc = {
        "user_id": str(user_id),
        "title": title,
        "body": body,
        "category": category if category in CATEGORIES else "system",
        "icon": icon,
        "link": link,
        "read": False,
        "created_at": now(),
    }
    result = await db.notifications.insert_one(doc)
    return str(result.inserted_id)


@router.get("")
async def list_notifications(
    page: int = 1,
    limit: int = 20,
    category: Optional[str] = None,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """List the current user's notifications (paginated, newest first)."""
    db = get_database()
    query = {"user_id": str(current_user["_id"])}
    if category and category in CATEGORIES:
        query["category"] = category
    if unread_only:
        query["read"] = False
    return await paginate(db.notifications, query, page, limit)


@router.get("/unread-count")
async def unread_count(current_user: dict = Depends(get_current_user)):
    """Return the unread notification count (drives the bell badge)."""
    db = get_database()
    count = await db.notifications.count_documents({"user_id": str(current_user["_id"]), "read": False})
    return {"unread": count}


@router.get("/{notification_id}")
async def get_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch a single notification (must belong to the caller)."""
    db = get_database()
    doc = await db.notifications.find_one({"_id": oid(notification_id), "user_id": str(current_user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="Notification not found")
    return serialize(doc)


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Mark one notification as read."""
    db = get_database()
    result = await db.notifications.update_one(
        {"_id": oid(notification_id), "user_id": str(current_user["_id"])},
        {"$set": {"read": True, "read_at": now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as read"}


@router.patch("/{notification_id}/unread")
async def mark_unread(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Mark one notification back to unread."""
    db = get_database()
    result = await db.notifications.update_one(
        {"_id": oid(notification_id), "user_id": str(current_user["_id"])},
        {"$set": {"read": False}, "$unset": {"read_at": ""}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Marked as unread"}


@router.post("/read-all")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    """Mark every notification for the caller as read."""
    db = get_database()
    result = await db.notifications.update_many(
        {"user_id": str(current_user["_id"]), "read": False},
        {"$set": {"read": True, "read_at": now()}},
    )
    return {"message": "All marked as read", "updated": result.modified_count}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, current_user: dict = Depends(get_current_user)):
    """Delete one notification."""
    db = get_database()
    result = await db.notifications.delete_one({"_id": oid(notification_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Deleted"}


@router.delete("")
async def clear_all(current_user: dict = Depends(get_current_user)):
    """Clear all of the caller's notifications."""
    db = get_database()
    result = await db.notifications.delete_many({"user_id": str(current_user["_id"])})
    return {"message": "Cleared", "deleted": result.deleted_count}


# ---- Admin: create / broadcast ------------------------------------------------

@router.post("/admin/create")
async def admin_create(payload: NotificationCreate, current_admin: dict = Depends(require_admin)):
    """Admin sends a notification to one specific user."""
    nid = await push_notification(
        payload.user_id, payload.title, payload.body, payload.category, payload.icon, payload.link
    )
    await audit("notification.create", current_admin, target=payload.user_id)
    return {"message": "Sent", "id": nid}


@router.post("/admin/broadcast")
async def admin_broadcast(payload: BroadcastCreate, current_admin: dict = Depends(require_admin)):
    """Admin broadcasts a notification to every user of a role (or everyone)."""
    db = get_database()
    query = {} if payload.role == "all" else {"role": payload.role}
    users = await db.users.find(query, {"_id": 1}).to_list(length=100000)
    if not users:
        return {"message": "No recipients", "sent": 0}
    docs = [{
        "user_id": str(u["_id"]),
        "title": payload.title,
        "body": payload.body,
        "category": payload.category if payload.category in CATEGORIES else "announcement",
        "icon": None,
        "link": None,
        "read": False,
        "created_at": now(),
    } for u in users]
    await db.notifications.insert_many(docs)
    await audit("notification.broadcast", current_admin, meta={"count": len(docs), "role": payload.role})
    return {"message": "Broadcast sent", "sent": len(docs)}
