"""Moderation router — report content and admin review queue.

Users report inappropriate content (feedback, messages, suggestions). Admins work
a moderation queue and take action.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, paginate, oid, audit, now

router = APIRouter(prefix="/api/moderation", tags=["moderation"])

REASONS = ["spam", "abuse", "inappropriate", "off_topic", "other"]
STATUSES = ["pending", "reviewed", "actioned", "dismissed"]


class ReportCreate(BaseModel):
    target_type: str = Field(description="message | suggestion | feedback | content")
    target_id: str
    reason: str = "other"
    detail: Optional[str] = Field(default=None, max_length=1000)


class ReviewAction(BaseModel):
    status: str
    note: Optional[str] = None


@router.post("/report")
async def report(payload: ReportCreate, current_user: dict = Depends(get_current_user)):
    """File a content report."""
    db = get_database()
    doc = {
        "reporter_id": str(current_user["_id"]), "target_type": payload.target_type, "target_id": payload.target_id,
        "reason": payload.reason if payload.reason in REASONS else "other", "detail": payload.detail,
        "status": "pending", "created_at": now(),
    }
    result = await db.reports.insert_one(doc)
    doc["_id"] = result.inserted_id
    return {"message": "Report submitted", "id": str(result.inserted_id)}


@router.get("/queue")
async def queue(page: int = 1, limit: int = 20, status: Optional[str] = None, current_admin: dict = Depends(require_admin)):
    """Admin: moderation queue."""
    db = get_database()
    query = {"status": status} if status in STATUSES else {}
    return await paginate(db.reports, query, page, limit)


@router.get("/stats")
async def stats(current_admin: dict = Depends(require_admin)):
    """Admin: report counts by status and reason."""
    db = get_database()
    by_status = {s: await db.reports.count_documents({"status": s}) for s in STATUSES}
    by_reason = {r: await db.reports.count_documents({"reason": r}) for r in REASONS}
    return {"by_status": by_status, "by_reason": by_reason, "total": await db.reports.count_documents({})}


@router.patch("/{report_id}")
async def review(report_id: str, payload: ReviewAction, current_admin: dict = Depends(require_admin)):
    """Admin: action a report."""
    db = get_database()
    if payload.status not in STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    result = await db.reports.update_one(
        {"_id": oid(report_id)},
        {"$set": {"status": payload.status, "review_note": payload.note, "reviewed_by": current_admin.get("email"), "reviewed_at": now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Report not found")
    await audit("moderation.review", current_admin, target=report_id, meta={"status": payload.status})
    return serialize(await db.reports.find_one({"_id": oid(report_id)}))
