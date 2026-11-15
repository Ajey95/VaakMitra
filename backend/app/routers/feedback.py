"""Feedback router — in-app feedback, bug reports and feature requests.

Backs the Feedback page. Users submit feedback; admins triage it (status,
priority) and respond. A public NPS-style rating summary powers testimonials.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now
from .notifications import push_notification

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

TYPES = ["general", "bug", "feature", "praise", "complaint"]
STATUSES = ["open", "in_review", "planned", "resolved", "closed"]


class FeedbackCreate(BaseModel):
    type: str = Field(default="general")
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    page: Optional[str] = None


class FeedbackTriage(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None  # low | medium | high
    admin_response: Optional[str] = None


@router.post("")
async def submit_feedback(payload: FeedbackCreate, current_user: dict = Depends(get_current_user)):
    """Submit feedback tied to the current user."""
    db = get_database()
    doc = {
        "user_id": str(current_user["_id"]),
        "user_email": current_user.get("email"),
        "user_name": current_user.get("full_name"),
        "type": payload.type if payload.type in TYPES else "general",
        "subject": payload.subject,
        "message": payload.message,
        "rating": payload.rating,
        "page": payload.page,
        "status": "open",
        "priority": "medium",
        "admin_response": None,
        "created_at": now(),
        "updated_at": now(),
    }
    result = await db.feedback.insert_one(doc)
    return {"message": "Thank you for your feedback!", "id": str(result.inserted_id)}


@router.get("/mine")
async def my_feedback(page: int = 1, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """List feedback submitted by the caller."""
    db = get_database()
    return await paginate(db.feedback, {"user_id": str(current_user["_id"])}, page, limit)


@router.get("/summary")
async def feedback_summary(current_user: dict = Depends(get_current_user)):
    """Aggregate rating stats (average, distribution) — used for testimonials."""
    db = get_database()
    rows = await db.feedback.find({"rating": {"$ne": None}}, {"rating": 1}).to_list(length=100000)
    ratings = [r["rating"] for r in rows if r.get("rating")]
    dist = {str(i): ratings.count(i) for i in range(1, 6)}
    avg = round(sum(ratings) / len(ratings), 2) if ratings else 0
    return {"average_rating": avg, "total_ratings": len(ratings), "distribution": dist}


# ---- Admin triage -------------------------------------------------------------

@router.get("/admin/all")
async def admin_list(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    type: Optional[str] = None,
    current_admin: dict = Depends(require_admin),
):
    """Admin: list all feedback with filters."""
    db = get_database()
    query = {}
    if status in STATUSES:
        query["status"] = status
    if type in TYPES:
        query["type"] = type
    return await paginate(db.feedback, query, page, limit)


@router.get("/admin/stats")
async def admin_stats(current_admin: dict = Depends(require_admin)):
    """Admin: counts by status and type."""
    db = get_database()
    by_status = {s: await db.feedback.count_documents({"status": s}) for s in STATUSES}
    by_type = {t: await db.feedback.count_documents({"type": t}) for t in TYPES}
    total = await db.feedback.count_documents({})
    return {"total": total, "by_status": by_status, "by_type": by_type}


@router.patch("/admin/{feedback_id}")
async def admin_triage(feedback_id: str, payload: FeedbackTriage, current_admin: dict = Depends(require_admin)):
    """Admin: update status/priority and optionally respond (notifies the user)."""
    db = get_database()
    fb = await db.feedback.find_one({"_id": oid(feedback_id)})
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    updates = {"updated_at": now()}
    if payload.status and payload.status in STATUSES:
        updates["status"] = payload.status
    if payload.priority in ("low", "medium", "high"):
        updates["priority"] = payload.priority
    if payload.admin_response is not None:
        updates["admin_response"] = payload.admin_response
    await db.feedback.update_one({"_id": oid(feedback_id)}, {"$set": updates})
    if payload.admin_response:
        await push_notification(
            fb["user_id"], "Response to your feedback",
            payload.admin_response, category="system", link="/feedback",
        )
    await audit("feedback.triage", current_admin, target=feedback_id, meta=updates)
    doc = await db.feedback.find_one({"_id": oid(feedback_id)})
    return serialize(doc)


@router.delete("/admin/{feedback_id}")
async def admin_delete(feedback_id: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a feedback entry."""
    db = get_database()
    result = await db.feedback.delete_one({"_id": oid(feedback_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Feedback not found")
    await audit("feedback.delete", current_admin, target=feedback_id)
    return {"message": "Deleted"}
