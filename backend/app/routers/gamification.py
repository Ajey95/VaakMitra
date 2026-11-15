"""Gamification router: achievements and leaderboard derived from real data.

These endpoints read existing collections (users, progress, evaluations) — no
new schema. Badge unlock logic lives in `evaluate_badges`, a pure function that
is unit-tested directly.
"""
from typing import Dict, List

from fastapi import APIRouter, Depends

from ..database import get_database
from ..utils.jwt_handler import get_current_user, resolve_user_id


router = APIRouter(prefix="/api", tags=["gamification"])


# Canonical badge catalog (single source of truth for web + Android).
# metric is one of: stars, sessions, lessons, high_accuracy.
BADGES: List[Dict] = [
    {"id": "first_words", "title": "First Words", "icon": "🌱", "category": "Practice",
     "description": "Earn your first star", "metric": "stars", "threshold": 1},
    {"id": "rising_star", "title": "Rising Star", "icon": "⭐", "category": "Practice",
     "description": "Earn 5 stars", "metric": "stars", "threshold": 5},
    {"id": "on_fire", "title": "On Fire", "icon": "🔥", "category": "Streaks",
     "description": "Earn 10 stars", "metric": "stars", "threshold": 10},
    {"id": "mic_master", "title": "Mic Master", "icon": "🎤", "category": "Mastery",
     "description": "Earn 20 stars", "metric": "stars", "threshold": 20},
    {"id": "champion", "title": "Champion", "icon": "🏆", "category": "Mastery",
     "description": "Earn 35 stars", "metric": "stars", "threshold": 35},
    {"id": "speech_king", "title": "Speech Star", "icon": "👑", "category": "Mastery",
     "description": "Earn 50 stars", "metric": "stars", "threshold": 50},
    {"id": "to_the_moon", "title": "To the Moon", "icon": "🚀", "category": "Special",
     "description": "Earn 75 stars", "metric": "stars", "threshold": 75},
    {"id": "legend", "title": "Legend", "icon": "💎", "category": "Special",
     "description": "Earn 100 stars", "metric": "stars", "threshold": 100},
    {"id": "first_session", "title": "Getting Started", "icon": "🎯", "category": "Practice",
     "description": "Complete your first session", "metric": "sessions", "threshold": 1},
    {"id": "dedicated", "title": "Dedicated", "icon": "📅", "category": "Streaks",
     "description": "Complete 10 sessions", "metric": "sessions", "threshold": 10},
    {"id": "committed", "title": "Committed", "icon": "💪", "category": "Streaks",
     "description": "Complete 25 sessions", "metric": "sessions", "threshold": 25},
    {"id": "explorer", "title": "Explorer", "icon": "🧭", "category": "Mastery",
     "description": "Complete 3 lessons", "metric": "lessons", "threshold": 3},
    {"id": "graduate", "title": "Graduate", "icon": "🎓", "category": "Mastery",
     "description": "Complete all 6 lessons", "metric": "lessons", "threshold": 6},
    {"id": "perfectionist", "title": "Perfectionist", "icon": "✨", "category": "Special",
     "description": "Score 90%+ in a session", "metric": "high_accuracy", "threshold": 1},
    {"id": "sharp_shooter", "title": "Sharp Shooter", "icon": "🎯", "category": "Special",
     "description": "Score 90%+ in 5 sessions", "metric": "high_accuracy", "threshold": 5},
]


def evaluate_badges(
    total_stars: int,
    total_sessions: int,
    completed_lessons: int,
    high_accuracy_count: int,
) -> List[Dict]:
    """Compute unlock state + progress for every badge. Pure / testable."""
    metrics = {
        "stars": total_stars,
        "sessions": total_sessions,
        "lessons": completed_lessons,
        "high_accuracy": high_accuracy_count,
    }
    out: List[Dict] = []
    for badge in BADGES:
        current = metrics.get(badge["metric"], 0)
        threshold = badge["threshold"]
        out.append({
            **badge,
            "current": current,
            "unlocked": current >= threshold,
            "progress": min(1.0, round(current / threshold, 3)) if threshold else 1.0,
        })
    return out


@router.get("/achievements/{user_id}")
async def get_achievements(user_id: str, current_user: dict = Depends(get_current_user)):
    """Return the user's badge catalog with unlock state from real stats."""
    user_id = resolve_user_id(current_user, user_id)

    db = get_database()
    user = await db.users.find_one({"_id": current_user["_id"]})
    progress_docs = await db.progress.find({"user_id": user_id}).to_list(length=100)
    completed_lessons = len([p for p in progress_docs if p.get("completed")])
    high_accuracy_count = await db.evaluations.count_documents(
        {"user_id": user_id, "accuracy": {"$gte": 90}}
    )

    badges = evaluate_badges(
        total_stars=user.get("total_stars", 0) if user else 0,
        total_sessions=user.get("total_sessions", 0) if user else 0,
        completed_lessons=completed_lessons,
        high_accuracy_count=high_accuracy_count,
    )
    unlocked = [b for b in badges if b["unlocked"]]
    return {
        "badges": badges,
        "unlocked_count": len(unlocked),
        "total_count": len(badges),
        "total_stars": user.get("total_stars", 0) if user else 0,
    }


@router.get("/leaderboard")
async def get_leaderboard(current_user: dict = Depends(get_current_user), limit: int = 10):
    """Top users by total stars. Names only (child name), no contact data."""
    db = get_database()
    limit = max(1, min(limit, 50))
    top = await db.users.find(
        {"role": {"$ne": "admin"}}
    ).sort("total_stars", -1).limit(limit).to_list(length=limit)

    me_id = str(current_user["_id"])
    leaderboard = []
    for rank, u in enumerate(top, start=1):
        name = u.get("child_name") or u.get("full_name") or "Star Learner"
        leaderboard.append({
            "rank": rank,
            "name": name,
            "stars": u.get("total_stars", 0),
            "sessions": u.get("total_sessions", 0),
            "is_me": str(u["_id"]) == me_id,
        })
    return {"leaderboard": leaderboard}
