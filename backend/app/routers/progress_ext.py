"""Progress extras — session history, per-lesson detail, export & cleanup.

Extends the progress router with richer read views and data-management endpoints
the dashboard/progress pages need.
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from typing import Optional
from datetime import timedelta
import csv
import io
from ..database import get_database
from ..utils.jwt_handler import get_current_user, resolve_user_id
from ..utils.mongo import serialize, paginate, oid, now

router = APIRouter(prefix="/api/progress", tags=["progress-ext"])


@router.get("/history/{user_id}")
async def session_history(user_id: str, page: int = 1, limit: int = 20, current_user: dict = Depends(get_current_user)):
    """Paginated raw session (evaluation) history for a user."""
    target = resolve_user_id(current_user, user_id)
    db = get_database()
    return await paginate(db.evaluations, {"user_id": target}, page, limit)


@router.get("/lesson/{user_id}/{lesson_id}")
async def lesson_detail(user_id: str, lesson_id: int, current_user: dict = Depends(get_current_user)):
    """All attempts + best for one lesson."""
    target = resolve_user_id(current_user, user_id)
    db = get_database()
    attempts = await db.evaluations.find({"user_id": target, "lesson_id": lesson_id}).sort("created_at", -1).to_list(length=200)
    prog = await db.progress.find_one({"user_id": target, "lesson_id": lesson_id})
    return {"lesson_id": lesson_id, "progress": serialize(prog), "attempts": serialize(attempts), "attempt_count": len(attempts)}


@router.get("/overview/{user_id}")
async def overview(user_id: str, current_user: dict = Depends(get_current_user)):
    """Compact overview: totals, last-7-day sessions, best lesson, weakest lesson."""
    target = resolve_user_id(current_user, user_id)
    db = get_database()
    week_ago = now() - timedelta(days=7)
    total = await db.evaluations.count_documents({"user_id": target})
    week = await db.evaluations.count_documents({"user_id": target, "created_at": {"$gte": week_ago}})
    prog = await db.progress.find({"user_id": target}).to_list(length=1000)
    best = max(prog, key=lambda p: p.get("best_accuracy", 0), default=None)
    worst = min(prog, key=lambda p: p.get("best_accuracy", 100), default=None)
    return {
        "total_sessions": total, "sessions_this_week": week,
        "lessons_touched": len(prog),
        "best_lesson": serialize(best), "weakest_lesson": serialize(worst),
    }


@router.get("/export/{user_id}")
async def export_progress(user_id: str, current_user: dict = Depends(get_current_user)):
    """Export a user's session history as CSV."""
    target = resolve_user_id(current_user, user_id)
    db = get_database()
    evals = await db.evaluations.find({"user_id": target}).sort("created_at", -1).to_list(length=100000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Lesson", "Phoneme", "Accuracy", "GOP", "MFCC", "Stars"])
    for e in evals:
        writer.writerow([e.get("created_at", ""), e.get("lesson_id", ""), e.get("phoneme", ""),
                         e.get("accuracy", ""), e.get("gop_score", ""), e.get("mfcc_score", ""), e.get("stars_earned", "")])
    content = output.getvalue()
    output.close()
    return Response(content=content, media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=progress_{now().strftime('%Y%m%d')}.csv"})


@router.delete("/evaluation/{evaluation_id}")
async def delete_evaluation(evaluation_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a single evaluation belonging to the caller (or any, for admin)."""
    db = get_database()
    ev = await db.evaluations.find_one({"_id": oid(evaluation_id)})
    if not ev:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if ev["user_id"] != str(current_user["_id"]) and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    await db.evaluations.delete_one({"_id": oid(evaluation_id)})
    return {"message": "Evaluation deleted"}
