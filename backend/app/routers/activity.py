"""Activity router — unified per-user activity timeline.

Aggregates recent events (sessions, quiz attempts, game plays, badge claims) into
one reverse-chronological feed for the dashboard 'recent activity' widget.
"""
from fastapi import APIRouter, Depends, Query
from datetime import timedelta
from ..database import get_database
from ..utils.jwt_handler import get_current_user, resolve_user_id
from ..utils.mongo import now

router = APIRouter(prefix="/api/activity", tags=["activity"])


async def _feed(db, user_id: str, limit: int):
    events = []
    for e in await db.evaluations.find({"user_id": user_id}).sort("created_at", -1).limit(limit).to_list(length=limit):
        events.append({"type": "session", "title": f"Practised {e.get('phoneme', 'a sound')}",
                       "detail": f"{round(e.get('accuracy', 0))}% accuracy", "at": e["created_at"]})
    for a in await db.quiz_attempts.find({"user_id": user_id}).sort("created_at", -1).limit(limit).to_list(length=limit):
        events.append({"type": "quiz", "title": f"Took {a.get('quiz_title', 'a quiz')}",
                       "detail": f"{a.get('score_pct', 0)}%", "at": a["created_at"]})
    for g in await db.game_scores.find({"user_id": user_id}).sort("created_at", -1).limit(limit).to_list(length=limit):
        events.append({"type": "game", "title": f"Played {g.get('game_slug', 'a game')}",
                       "detail": f"Score {g.get('score', 0)}", "at": g["created_at"]})
    for b in await db.badge_claims.find({"user_id": user_id}).sort("claimed_at", -1).limit(limit).to_list(length=limit):
        events.append({"type": "badge", "title": f"Earned badge {b.get('badge_slug', '')}",
                       "detail": f"+{b.get('coins', 0)} coins", "at": b["claimed_at"]})
    events.sort(key=lambda x: x["at"], reverse=True)
    for e in events:
        e["at"] = e["at"].isoformat()
    return events[:limit]


@router.get("")
async def my_activity(limit: int = Query(default=20, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    """Unified activity feed for the caller."""
    db = get_database()
    return {"activity": await _feed(db, str(current_user["_id"]), limit)}


@router.get("/{user_id}")
async def user_activity(user_id: str, limit: int = Query(default=20, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    """Activity feed for a specific user (self, or admin/therapist)."""
    target = resolve_user_id(current_user, user_id)
    db = get_database()
    return {"activity": await _feed(db, target, limit)}


@router.get("/summary/today")
async def today_summary(current_user: dict = Depends(get_current_user)):
    """Counts of today's activity by type."""
    db = get_database()
    uid = str(current_user["_id"])
    start = now().replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "sessions": await db.evaluations.count_documents({"user_id": uid, "created_at": {"$gte": start}}),
        "quizzes": await db.quiz_attempts.count_documents({"user_id": uid, "created_at": {"$gte": start}}),
        "games": await db.game_scores.count_documents({"user_id": uid, "created_at": {"$gte": start}}),
    }
