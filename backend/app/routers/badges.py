"""Badges router — claimable achievements that pay out coins.

Complements the read-only gamification/achievements endpoint. Here badges can be
*claimed* once their criteria are met, crediting the wallet. Admins can define
extra custom badges.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from ..database import get_database
from ..utils.jwt_handler import get_current_user, require_admin
from ..utils.mongo import serialize, oid, now
from .notifications import push_notification

router = APIRouter(prefix="/api/badges", tags=["badges"])

# Built-in badge definitions: (slug, title, metric, threshold, coin_reward).
BADGE_DEFS = [
    {"slug": "first-steps", "title": "First Steps", "metric": "sessions", "threshold": 1, "coins": 10, "icon": "👣"},
    {"slug": "getting-started", "title": "Getting Started", "metric": "sessions", "threshold": 5, "coins": 20, "icon": "🚀"},
    {"slug": "dedicated", "title": "Dedicated Learner", "metric": "sessions", "threshold": 25, "coins": 50, "icon": "📚"},
    {"slug": "star-collector", "title": "Star Collector", "metric": "stars", "threshold": 20, "coins": 40, "icon": "⭐"},
    {"slug": "star-master", "title": "Star Master", "metric": "stars", "threshold": 50, "coins": 80, "icon": "🌟"},
    {"slug": "sharp-shooter", "title": "Sharp Shooter", "metric": "high_accuracy", "threshold": 5, "coins": 60, "icon": "🎯"},
    {"slug": "lesson-finisher", "title": "Lesson Finisher", "metric": "lessons", "threshold": 3, "coins": 30, "icon": "🏁"},
]


class BadgeDef(BaseModel):
    slug: str
    title: str
    metric: str = "sessions"
    threshold: int = 1
    coins: int = 20
    icon: Optional[str] = None


async def _metrics(db, user_id: str) -> dict:
    user = await db.users.find_one({"_id": oid(user_id)})
    high_acc = await db.evaluations.count_documents({"user_id": user_id, "accuracy": {"$gte": 90}})
    lessons_done = await db.progress.count_documents({"user_id": user_id, "completed": True})
    return {
        "sessions": user.get("total_sessions", 0) if user else 0,
        "stars": user.get("total_stars", 0) if user else 0,
        "high_accuracy": high_acc,
        "lessons": lessons_done,
    }


async def _all_defs(db):
    custom = await db.custom_badges.find({}).to_list(length=200)
    return BADGE_DEFS + [{"slug": c["slug"], "title": c["title"], "metric": c["metric"],
                          "threshold": c["threshold"], "coins": c["coins"], "icon": c.get("icon")} for c in custom]


@router.get("")
async def list_badges(current_user: dict = Depends(get_current_user)):
    """List all badges with unlocked/claimed state and progress for the caller."""
    db = get_database()
    uid = str(current_user["_id"])
    metrics = await _metrics(db, uid)
    claimed = {c["badge_slug"] for c in await db.badge_claims.find({"user_id": uid}).to_list(length=500)}
    out = []
    for d in await _all_defs(db):
        current = metrics.get(d["metric"], 0)
        unlocked = current >= d["threshold"]
        out.append({
            **d, "current": current, "unlocked": unlocked,
            "claimed": d["slug"] in claimed,
            "progress_pct": min(100, round(current / d["threshold"] * 100, 1)) if d["threshold"] else 100,
        })
    return {"badges": out, "unlocked_count": sum(1 for b in out if b["unlocked"]),
            "claimed_count": sum(1 for b in out if b["claimed"])}


@router.post("/{badge_slug}/claim")
async def claim_badge(badge_slug: str, current_user: dict = Depends(get_current_user)):
    """Claim an unlocked badge's coin reward (once)."""
    db = get_database()
    uid = str(current_user["_id"])
    defs = {d["slug"]: d for d in await _all_defs(db)}
    badge = defs.get(badge_slug)
    if not badge:
        raise HTTPException(status_code=404, detail="Badge not found")
    if await db.badge_claims.find_one({"user_id": uid, "badge_slug": badge_slug}):
        raise HTTPException(status_code=409, detail="Already claimed")
    metrics = await _metrics(db, uid)
    if metrics.get(badge["metric"], 0) < badge["threshold"]:
        raise HTTPException(status_code=400, detail="Badge not unlocked yet")
    await db.badge_claims.insert_one({"user_id": uid, "badge_slug": badge_slug, "coins": badge["coins"], "claimed_at": now()})
    from .wallet import credit_wallet
    await credit_wallet(uid, coins=badge["coins"], reason=f"Badge: {badge['title']}")
    await push_notification(uid, f"Badge unlocked: {badge['title']}", f"You earned {badge['coins']} coins!", category="achievement")
    return {"message": "Badge claimed", "coins": badge["coins"]}


@router.get("/claimed")
async def claimed_badges(current_user: dict = Depends(get_current_user)):
    """List the caller's claimed badges."""
    db = get_database()
    rows = await db.badge_claims.find({"user_id": str(current_user["_id"])}).sort("claimed_at", -1).to_list(length=500)
    return {"claimed": serialize(rows)}


@router.post("/admin")
async def create_badge(payload: BadgeDef, current_admin: dict = Depends(require_admin)):
    """Admin: define a custom badge."""
    db = get_database()
    if await db.custom_badges.find_one({"slug": payload.slug}):
        raise HTTPException(status_code=409, detail="Slug exists")
    doc = {**payload.model_dump(), "created_at": now()}
    result = await db.custom_badges.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)


@router.delete("/admin/{badge_slug}")
async def delete_badge(badge_slug: str, current_admin: dict = Depends(require_admin)):
    """Admin: delete a custom badge."""
    db = get_database()
    result = await db.custom_badges.delete_one({"slug": badge_slug})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Badge not found")
    return {"message": "Deleted"}
