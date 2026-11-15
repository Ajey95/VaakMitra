"""Support router — help tickets + FAQ.

Backs the Help page. Users open support tickets and browse a FAQ knowledge base
that admins curate.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, now
from .notifications import push_notification

router = APIRouter(prefix="/api/support", tags=["support"])

PRIORITIES = ["low", "medium", "high", "urgent"]
STATUSES = ["open", "pending", "resolved", "closed"]

DEFAULT_FAQ = [
    {"question": "How do I start a therapy lesson?", "answer": "Open Training, pick a lesson and follow the slides.", "category": "getting-started"},
    {"question": "How are stars earned?", "answer": "Stars are awarded based on your pronunciation accuracy each session.", "category": "rewards"},
    {"question": "Can a therapist see my child's progress?", "answer": "Yes, if you assign a therapist and enable sharing in Settings > Privacy.", "category": "privacy"},
]


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)
    priority: str = "medium"


class TicketReply(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    status: Optional[str] = None


class FaqCreate(BaseModel):
    question: str
    answer: str
    category: str = "general"


@router.post("/tickets")
async def create_ticket(payload: TicketCreate, current_user: dict = Depends(get_current_user)):
    """Open a support ticket."""
    db = get_database()
    doc = {
        "user_id": str(current_user["_id"]), "user_name": current_user.get("full_name"),
        "subject": payload.subject, "priority": payload.priority if payload.priority in PRIORITIES else "medium",
        "status": "open", "messages": [{"from": "user", "body": payload.message, "at": now().isoformat()}],
        "created_at": now(), "updated_at": now(),
    }
    result = await db.support_tickets.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("/tickets")
async def my_tickets(page: int = 1, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """List the caller's tickets."""
    db = get_database()
    return await paginate(db.support_tickets, {"user_id": str(current_user["_id"])}, page, limit)


@router.get("/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch a ticket thread (owner or admin)."""
    db = get_database()
    t = await db.support_tickets.find_one({"_id": oid(ticket_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if t["user_id"] != str(current_user["_id"]) and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return serialize(t)


@router.post("/tickets/{ticket_id}/reply")
async def reply_ticket(ticket_id: str, payload: TicketReply, current_user: dict = Depends(get_current_user)):
    """Reply to a ticket (user or admin); admin can also change status."""
    db = get_database()
    t = await db.support_tickets.find_one({"_id": oid(ticket_id)})
    if not t:
        raise HTTPException(status_code=404, detail="Ticket not found")
    is_admin = current_user.get("role") == "admin"
    if t["user_id"] != str(current_user["_id"]) and not is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    entry = {"from": "admin" if is_admin else "user", "body": payload.message, "at": now().isoformat()}
    updates = {"updated_at": now()}
    if is_admin and payload.status in STATUSES:
        updates["status"] = payload.status
    await db.support_tickets.update_one({"_id": oid(ticket_id)}, {"$push": {"messages": entry}, "$set": updates})
    if is_admin:
        await push_notification(t["user_id"], "Support replied to your ticket", payload.message[:80], category="system", link="/help")
    return serialize(await db.support_tickets.find_one({"_id": oid(ticket_id)}))


@router.get("/tickets/admin/all")
async def admin_tickets(page: int = 1, limit: int = 30, status: Optional[str] = None, current_admin: dict = Depends(require_admin)):
    """Admin: list all tickets."""
    db = get_database()
    query = {"status": status} if status in STATUSES else {}
    return await paginate(db.support_tickets, query, page, limit)


# ---- FAQ ----------------------------------------------------------------------

@router.get("/faq")
async def list_faq(category: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List FAQ entries (seeds defaults on first call)."""
    db = get_database()
    if await db.faq.count_documents({}) == 0:
        await db.faq.insert_many([{**f, "created_at": now()} for f in DEFAULT_FAQ])
    query = {"category": category} if category else {}
    rows = await db.faq.find(query).to_list(length=500)
    return {"faq": serialize(rows)}


@router.post("/faq/admin")
async def create_faq(payload: FaqCreate, current_admin: dict = Depends(require_admin)):
    """Admin: add an FAQ entry."""
    db = get_database()
    doc = {**payload.model_dump(), "created_at": now()}
    result = await db.faq.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.delete("/faq/admin/{faq_id}")
async def delete_faq(faq_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete an FAQ entry."""
    db = get_database()
    result = await db.faq.delete_one({"_id": oid(faq_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"message": "Deleted"}
