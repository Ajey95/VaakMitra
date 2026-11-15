"""Enquiries router — user enquiries / requests with a status timeline.

Backs the app's "My enquiries" screen. A user raises an enquiry (question,
demo request, therapy plan request); admins respond and move it through a
status timeline that the user can watch.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now
from .notifications import push_notification

router = APIRouter(prefix="/api/enquiries", tags=["enquiries"])

STATUSES = ["new", "in_progress", "responded", "resolved", "closed"]
CATEGORIES = ["general", "therapy_plan", "demo", "billing", "technical"]


class EnquiryCreate(BaseModel):
    category: str = "general"
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)


class EnquiryResponse(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    status: Optional[str] = None


@router.post("")
async def create_enquiry(payload: EnquiryCreate, current_user: dict = Depends(get_current_user)):
    """Raise a new enquiry."""
    db = get_database()
    doc = {
        "user_id": str(current_user["_id"]), "user_name": current_user.get("full_name"),
        "user_email": current_user.get("email"),
        "category": payload.category if payload.category in CATEGORIES else "general",
        "subject": payload.subject, "message": payload.message, "status": "new",
        "timeline": [{"status": "new", "note": "Enquiry raised", "at": now().isoformat()}],
        "created_at": now(), "updated_at": now(),
    }
    result = await db.enquiries.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.get("")
async def my_enquiries(page: int = 1, limit: int = 20, status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """List the caller's enquiries."""
    db = get_database()
    query = {"user_id": str(current_user["_id"])}
    if status in STATUSES:
        query["status"] = status
    return await paginate(db.enquiries, query, page, limit)


@router.get("/{enquiry_id}")
async def get_enquiry(enquiry_id: str, current_user: dict = Depends(get_current_user)):
    """Fetch one enquiry with its full timeline (owner or admin)."""
    db = get_database()
    enq = await db.enquiries.find_one({"_id": oid(enquiry_id)})
    if not enq:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    if enq["user_id"] != str(current_user["_id"]) and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    return serialize(enq)


@router.get("/admin/all")
async def admin_all(page: int = 1, limit: int = 30, status: Optional[str] = None, current_admin: dict = Depends(require_admin)):
    """Admin: list all enquiries."""
    db = get_database()
    query = {"status": status} if status in STATUSES else {}
    return await paginate(db.enquiries, query, page, limit)


@router.post("/admin/{enquiry_id}/respond")
async def admin_respond(enquiry_id: str, payload: EnquiryResponse, current_admin: dict = Depends(require_admin)):
    """Admin: respond and advance the status timeline (notifies the user)."""
    db = get_database()
    enq = await db.enquiries.find_one({"_id": oid(enquiry_id)})
    if not enq:
        raise HTTPException(status_code=404, detail="Enquiry not found")
    new_status = payload.status if payload.status in STATUSES else "responded"
    entry = {"status": new_status, "note": payload.message, "by": current_admin.get("full_name"), "at": now().isoformat()}
    await db.enquiries.update_one(
        {"_id": oid(enquiry_id)},
        {"$set": {"status": new_status, "updated_at": now()}, "$push": {"timeline": entry}},
    )
    await push_notification(enq["user_id"], "Update on your enquiry", payload.message[:80], category="system", link="/enquiries")
    await audit("enquiry.respond", current_admin, target=enquiry_id, meta={"status": new_status})
    return serialize(await db.enquiries.find_one({"_id": oid(enquiry_id)}))
